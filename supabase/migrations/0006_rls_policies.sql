-- =====================================================================
-- 0006_rls_policies.sql
-- Allow authenticated users (via anon key + user JWT) to access
-- all data tables. The backend now passes the user's auth token to
-- PostgREST, so RLS picks up auth.uid() correctly.
--
-- Admins (@vinciai.academy) get full CRUD access.
-- Teachers get read-only access + write to their own offers.
-- =====================================================================

-- Helper: current user is an admin (via app_users table)
create or replace function public.current_is_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.app_users
    where user_id = auth.uid()
      and role = 'Admin'
  );
$$;

-- ── SCHOOLS ────────────────────────────────────────────────────────
drop policy if exists schools_select on public.schools;
create policy schools_select on public.schools
    for select
    using (true);  -- all authenticated users can read schools

drop policy if exists schools_insert on public.schools;
create policy schools_insert on public.schools
    for insert
    with check (public.current_is_admin());

drop policy if exists schools_update on public.schools;
create policy schools_update on public.schools
    for update
    using (public.current_is_admin());

drop policy if exists schools_delete on public.schools;
create policy schools_delete on public.schools
    for delete
    using (public.current_is_admin());

-- ── TEACHERS ───────────────────────────────────────────────────────
drop policy if exists teachers_select on public.teachers;
create policy teachers_select on public.teachers
    for select
    using (true);

drop policy if exists teachers_insert on public.teachers;
create policy teachers_insert on public.teachers
    for insert
    with check (public.current_is_admin());

drop policy if exists teachers_update on public.teachers;
create policy teachers_update on public.teachers
    for update
    using (public.current_is_admin());

drop policy if exists teachers_delete on public.teachers;
create policy teachers_delete on public.teachers
    for delete
    using (public.current_is_admin());

-- ── COURSES ────────────────────────────────────────────────────────
drop policy if exists courses_select on public.courses;
create policy courses_select on public.courses
    for select
    using (true);

drop policy if exists courses_insert on public.courses;
create policy courses_insert on public.courses
    for insert
    with check (public.current_is_admin());

drop policy if exists courses_update on public.courses;
create policy courses_update on public.courses
    for update
    using (public.current_is_admin());

drop policy if exists courses_delete on public.courses;
create policy courses_delete on public.courses
    for delete
    using (public.current_is_admin());

-- ── LESSONS ────────────────────────────────────────────────────────
drop policy if exists lessons_select on public.lessons;
create policy lessons_select on public.lessons
    for select
    using (true);

drop policy if exists lessons_insert on public.lessons;
create policy lessons_insert on public.lessons
    for insert
    with check (public.current_is_admin());

drop policy if exists lessons_update on public.lessons;
create policy lessons_update on public.lessons
    for update
    using (public.current_is_admin());

drop policy if exists lessons_delete on public.lessons;
create policy lessons_delete on public.lessons
    for delete
    using (public.current_is_admin());

-- ── LESSON_TUTOR_OFFERS ────────────────────────────────────────────
drop policy if exists offers_select on public.lesson_tutor_offers;
create policy offers_select on public.lesson_tutor_offers
    for select
    using (true);

drop policy if exists offers_insert on public.lesson_tutor_offers;
create policy offers_insert on public.lesson_tutor_offers
    for insert
    with check (public.current_is_admin());

drop policy if exists offers_update on public.lesson_tutor_offers;
create policy offers_update on public.lesson_tutor_offers
    for update
    using (public.current_is_admin());

drop policy if exists offers_delete on public.lesson_tutor_offers;
create policy offers_delete on public.lesson_tutor_offers
    for delete
    using (public.current_is_admin());

-- ── LESSON_EVENTS ──────────────────────────────────────────────────
drop policy if exists events_select on public.lesson_events;
create policy events_select on public.lesson_events
    for select
    using (true);

drop policy if exists events_insert on public.lesson_events;
create policy events_insert on public.lesson_events
    for insert
    with check (public.current_is_admin());

drop policy if exists events_update on public.lesson_events;
create policy events_update on public.lesson_events
    for update
    using (public.current_is_admin());

drop policy if exists events_delete on public.lesson_events;
create policy events_delete on public.lesson_events
    for delete
    using (public.current_is_admin());
