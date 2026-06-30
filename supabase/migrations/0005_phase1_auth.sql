-- =====================================================================
-- 0005_phase1_auth.sql
-- Phase 1 — Platform Foundation: Authentication identity & roles.
--
-- Implements Business Rules v1.2 Section 3 (Authentication), Section 18
-- (first sign-in role logic) and Section 8.8 (app_users table).
--
--   * Vinci-domain email (@vinciai.academy) -> role 'Admin'
--   * else match teachers.email -> role 'Teacher' + link teacher record
--   * else NO app_users row is created -> the app shows the
--     "Unauthorized, request registration" page.
--
-- No public self-registration: rows in app_users are only created by the
-- on-auth-user-created trigger below, and only for trusted identities.
--
-- This migration is additive and idempotent; it does not touch existing
-- tables other than adding teachers.auth_user_id.
-- =====================================================================

-- ---------------------------------------------------------------------
-- Vinci domain helper. Centralised so the domain list lives in one place.
-- Section 3: "Vinci domain: @vinciai.academy, for admin only access."
-- ---------------------------------------------------------------------
create or replace function public.is_vinci_email(p_email text)
returns boolean
language sql
immutable
as $$
  select lower(split_part(coalesce(p_email, ''), '@', 2)) = 'vinciai.academy';
$$;

-- ---------------------------------------------------------------------
-- teachers.auth_user_id — links a teacher record to its login identity.
-- NULL until the teacher first signs in (Section 8.4 / FK catalogue).
-- ---------------------------------------------------------------------
alter table public.teachers
    add column if not exists auth_user_id uuid;

do $$
begin
    if not exists (
        select 1 from pg_constraint where conname = 'teachers_auth_user_id_fkey'
    ) then
        alter table public.teachers
            add constraint teachers_auth_user_id_fkey
            foreign key (auth_user_id) references auth.users (id) on delete set null;
    end if;
exception when undefined_table then
    -- auth schema not present (e.g. local pg without supabase). Skip FK.
    null;
end $$;

create unique index if not exists uq_teachers_auth_user_id
    on public.teachers (auth_user_id)
    where auth_user_id is not null;

-- ---------------------------------------------------------------------
-- app_users — Auth Identity & Roles (Section 8.8).
-- 1:1 with auth.users. user_id IS the Supabase auth user id.
-- ---------------------------------------------------------------------
create table if not exists public.app_users (
    user_id        uuid primary key references auth.users (id) on delete cascade,
    email          text not null,
    role           text not null default 'Teacher' check (role in ('Admin', 'Teacher')),
    is_vinci_email boolean not null default false,
    teacher_id     text references public.teachers (teacher_id) on delete set null,
    display_name   text,
    created_at     timestamptz not null default now()
);

create unique index if not exists uq_app_users_email      on public.app_users (lower(email));
create unique index if not exists uq_app_users_teacher_id on public.app_users (teacher_id)
    where teacher_id is not null;

-- ---------------------------------------------------------------------
-- handle_new_user() — runs after a row is inserted into auth.users.
-- Implements Section 18 role-assignment logic. If the identity is neither
-- a Vinci email nor a known teacher email, NO app_users row is created,
-- so the frontend treats the account as "Unauthorized".
-- ---------------------------------------------------------------------
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
    v_email      text := lower(coalesce(new.email, ''));
    v_is_vinci   boolean := public.is_vinci_email(v_email);
    v_teacher_id text;
    v_name       text := coalesce(
        new.raw_user_meta_data ->> 'full_name',
        new.raw_user_meta_data ->> 'name',
        split_part(v_email, '@', 1)
    );
begin
    if v_email = '' then
        return new;
    end if;

    if v_is_vinci then
        -- Vinci staff -> Admin, full access.
        insert into public.app_users (user_id, email, role, is_vinci_email, display_name)
        values (new.id, v_email, 'Admin', true, v_name)
        on conflict (user_id) do update
            set email = excluded.email,
                role = 'Admin',
                is_vinci_email = true;
        return new;
    end if;

    -- Non-Vinci: must match a pre-registered teacher email (Section 3 / 18).
    select t.teacher_id into v_teacher_id
    from public.teachers t
    where lower(t.email) = v_email
    limit 1;

    if v_teacher_id is not null then
        insert into public.app_users (user_id, email, role, is_vinci_email, teacher_id, display_name)
        values (new.id, v_email, 'Teacher', false, v_teacher_id, v_name)
        on conflict (user_id) do update
            set email = excluded.email,
                role = 'Teacher',
                teacher_id = excluded.teacher_id;

        -- Auto-link the auth identity to the teacher record (Section 18).
        update public.teachers
        set auth_user_id = new.id
        where teacher_id = v_teacher_id
          and auth_user_id is null;
    end if;
    -- else: no app_users row -> Unauthorized (request registration).

    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

-- ---------------------------------------------------------------------
-- Role helper functions for RLS (read the caller's app_users row).
-- ---------------------------------------------------------------------
create or replace function public.current_app_role()
returns text
language sql
stable
security definer
set search_path = public
as $$
  select role from public.app_users where user_id = auth.uid();
$$;

create or replace function public.is_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select coalesce(public.current_app_role() = 'Admin', false);
$$;

create or replace function public.current_teacher_id()
returns text
language sql
stable
security definer
set search_path = public
as $$
  select teacher_id from public.app_users where user_id = auth.uid();
$$;

-- ---------------------------------------------------------------------
-- RLS on app_users: a user can read their own profile; admins read all.
-- The backend uses the service_role key which bypasses RLS entirely.
-- ---------------------------------------------------------------------
alter table public.app_users enable row level security;

drop policy if exists app_users_self_select on public.app_users;
create policy app_users_self_select on public.app_users
    for select
    using (user_id = auth.uid() or public.is_admin());

-- ---------------------------------------------------------------------
-- Backfill: create app_users rows for any auth.users that already exist
-- (e.g. created before this trigger). Safe to run repeatedly.
-- ---------------------------------------------------------------------
insert into public.app_users (user_id, email, role, is_vinci_email, teacher_id, display_name)
select u.id,
       lower(u.email),
       case
           when public.is_vinci_email(u.email) then 'Admin'
           when t.teacher_id is not null then 'Teacher'
           else 'Teacher'
       end as role,
       public.is_vinci_email(u.email),
       t.teacher_id,
       split_part(lower(u.email), '@', 1)
from auth.users u
left join public.teachers t on lower(t.email) = lower(u.email)
where u.email is not null
  and (public.is_vinci_email(u.email) or t.teacher_id is not null)
  and not exists (select 1 from public.app_users a where a.user_id = u.id)
on conflict (user_id) do nothing;
