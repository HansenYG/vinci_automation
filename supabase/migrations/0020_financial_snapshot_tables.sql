-- =====================================================================
-- 0020_financial_snapshot_tables.sql
-- Create teacher_salary_snapshots and course_financial_snapshots tables
-- for the monthly finance snapshot job (Business Rules s.10).
-- =====================================================================

begin;

-- Monthly teacher salary snapshots
create table if not exists public.teacher_salary_snapshots (
  id              uuid primary key default gen_random_uuid(),
  teacher_id      text not null references public.teachers(teacher_id) on delete cascade,
  teacher_name    text not null,
  year            integer not null,
  month           integer not null,
  tutor_hours     numeric(10,2) not null default 0,
  ta_hours        numeric(10,2) not null default 0,
  tutor_rate      numeric(10,2) not null default 0,
  ta_rate         numeric(10,2) not null default 0,
  tutor_payout    numeric(12,2) not null default 0,
  ta_payout       numeric(12,2) not null default 0,
  total_payout    numeric(12,2) not null default 0,
  lessons_count   integer not null default 0,
  created_at      timestamptz not null default now(),
  unique (teacher_id, year, month)
);

comment on table public.teacher_salary_snapshots is
  'Monthly salary report per teacher. Rows upserted by monthly-finance-snapshot job.';

-- Monthly course financial snapshots
create table if not exists public.course_financial_snapshots (
  id              uuid primary key default gen_random_uuid(),
  course_id       text not null references public.courses(course_id) on delete cascade,
  course_name     text not null,
  school_name     text,
  year            integer not null,
  month           integer not null,
  total_income    numeric(12,2) not null default 0,
  total_expenses  numeric(12,2) not null default 0,
  profit_loss     numeric(12,2) not null default 0,
  profit_loss_pct numeric(5,2),
  lessons_count   integer not null default 0,
  created_at      timestamptz not null default now(),
  unique (course_id, year, month)
);

comment on table public.course_financial_snapshots is
  'Monthly P/L report per course. Rows upserted by monthly-finance-snapshot job.';

-- Indexes for common query patterns
create index if not exists idx_salary_snapshots_period
  on public.teacher_salary_snapshots (year, month);

create index if not exists idx_course_snapshots_period
  on public.course_financial_snapshots (year, month);

-- RLS: only admins can read (service-role can write via cron)
alter table public.teacher_salary_snapshots enable row level security;
alter table public.course_financial_snapshots enable row level security;

create policy "Admins can read salary snapshots"
  on public.teacher_salary_snapshots for select
  using (public.is_admin());

create policy "Admins can read course snapshots"
  on public.course_financial_snapshots for select
  using (public.is_admin());

-- Service-role can insert/update (for the snapshot job)
create policy "Service role can manage salary snapshots"
  on public.teacher_salary_snapshots for all
  using (true) with check (true);

create policy "Service role can manage course snapshots"
  on public.course_financial_snapshots for all
  using (true) with check (true);

commit;
