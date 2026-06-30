-- =====================================================================
-- Vinci Automation — schema mirroring the 4 Airtable tables
-- (Schools, Teachers, Courses, Lessons) exactly.
--
-- Modelling rule (per the brief): a foreign key is the ANCHOR for the
-- related record's data. We therefore store each table's INTRINSIC fields
-- as real columns, store links as real FK columns, and reproduce every
-- Airtable lookup / rollup column ("... (from Teacher)", "Total Revenue",
-- etc.) in a *_full VIEW that joins through the FK — so e.g. a lesson's
-- teacher name/email/rate come live from the Teacher row, never duplicated.
--
-- Natural keys are used as PKs to match Airtable:
--   schools.school_id, teachers.teacher_id, courses.course_id
-- Lessons keep a surrogate uuid id (many Airtable rows have a blank
-- Lesson ID) plus the Lesson ID as an attribute.
--
-- Run order: 0001 (this) then 0002_seed_airtable.sql.
-- =====================================================================

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------
-- SCHOOLS  (PK: School ID)
-- ---------------------------------------------------------------------
create table if not exists public.schools (
    school_id                     text primary key,
    school_name                   text,
    tutor_availability_submissions text,   -- raw linked value (no availability table yet)
    tutor_availability_slots      text,
    created_at                    timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- TEACHERS  (PK: Teacher ID) — intrinsic columns only; rollups in view
-- ---------------------------------------------------------------------
create table if not exists public.teachers (
    teacher_id                 text primary key,
    teacher_name               text,
    email                      text,
    whatsapp_number            text,
    status                     text,
    availability_description   text,
    tutor_rate                 numeric(10, 2),   -- Tutor Rate (HKD/hour)
    ta_rate                    numeric(10, 2),   -- TA Rate (HKD/hour)
    active_status              integer,
    hours_score                numeric,
    skill_score                numeric,          -- Skill Score (Number)
    reliability_score          numeric,
    sick_leave_count           integer,
    reschedule_count           integer,
    availability_slots         integer,          -- numeric slot count
    lessons_assigned_number    integer,
    background                 text,
    courses_can_teach          text,
    skill_matches              text,
    cv_link                    text,
    last_score_updated         timestamptz,
    completed_teaching_hours   numeric,          -- Completed Teaching Hours (Scoring)
    last_completed_lesson_date date,             -- Last Completed Lesson Date (Scoring)
    inactivity_penalty_applied boolean,
    score_last_updated         timestamptz,
    created_at                 timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- COURSES  (PK: Course ID; School ID FK anchors the school)
-- ---------------------------------------------------------------------
create table if not exists public.courses (
    course_id                   text primary key,
    course_name                 text,
    school_id                   text references public.schools (school_id) on delete set null,
    course_topic                text,
    course_types                text,
    revenue_per_lesson          numeric(12, 2),
    scheduled_classes_ai_summary text,
    created_at                  timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- LESSONS  (surrogate id; Lesson ID attribute; Teacher/Course FKs anchor
-- all the looked-up teacher & course data)
-- ---------------------------------------------------------------------
create table if not exists public.lessons (
    id                      uuid primary key default gen_random_uuid(),
    lesson_id               text,                                   -- Airtable "Lesson ID" (often blank)
    date                    date,
    start_time              time,
    end_time                time,
    teacher_id              text references public.teachers (teacher_id) on delete set null,  -- FK anchor
    course_id               text references public.courses (course_id) on delete set null,    -- FK anchor
    status                  text,            -- Scheduled / Completed / Cancelled / Rescheduled
    role                    text,            -- Tutor / Teaching Assistant
    lesson_duration_minutes integer,
    miscellaneous_expenses  numeric(12, 2),
    tutor_assignment        text,            -- Tutor assigned / unassigned & within|beyond a week
    offer_sent_timestamp    timestamptz,
    lesson_material_link    text,            -- *** extra field required by the design doc ***
    notes                   text,
    created_at              timestamptz not null default now(),
    updated_at              timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- LESSON_TUTOR_OFFERS — the WhatsApp pool / 24h re-blast bookkeeping
-- (not in Airtable; powers the automation). "Teacher's Accepted" is
-- represented here as offer_status = 'accepted'.
-- ---------------------------------------------------------------------
create table if not exists public.lesson_tutor_offers (
    id               uuid primary key default gen_random_uuid(),
    lesson_id        uuid not null references public.lessons (id) on delete cascade,
    teacher_id       text not null references public.teachers (teacher_id) on delete cascade,
    offer_status     text not null default 'pending'
                     check (offer_status in ('pending', 'accepted', 'declined', 'withdrawn')),
    last_blast_at    timestamptz,
    last_send_result text,
    responded_at     timestamptz,
    created_at       timestamptz not null default now(),
    unique (lesson_id, teacher_id)
);

-- ---------------------------------------------------------------------
-- LESSON_EVENTS — audit log (powers Urgent News + traceability)
-- ---------------------------------------------------------------------
create table if not exists public.lesson_events (
    id          uuid primary key default gen_random_uuid(),
    lesson_id   uuid references public.lessons (id) on delete cascade,
    teacher_id  text references public.teachers (teacher_id) on delete set null,
    event_type  text not null
                check (event_type in ('blast', 'reblast', 'accept', 'assign',
                                      'cancel', 'reschedule', 'confirmation_sent',
                                      'material_sent', 'admin_notified')),
    detail      jsonb,
    created_at  timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------
create index if not exists idx_lessons_date     on public.lessons (date);
create index if not exists idx_lessons_teacher   on public.lessons (teacher_id);
create index if not exists idx_lessons_course    on public.lessons (course_id);
create index if not exists idx_lessons_lesson_id on public.lessons (lesson_id);
create index if not exists idx_courses_school    on public.courses (school_id);
create index if not exists idx_offers_lesson     on public.lesson_tutor_offers (lesson_id);
create index if not exists idx_offers_teacher    on public.lesson_tutor_offers (teacher_id);
create index if not exists idx_teachers_whatsapp on public.teachers (whatsapp_number);
create index if not exists idx_events_lesson     on public.lesson_events (lesson_id);

-- ---------------------------------------------------------------------
-- updated_at trigger for lessons
-- ---------------------------------------------------------------------
create or replace function public.set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_lessons_updated_at on public.lessons;
create trigger trg_lessons_updated_at
    before update on public.lessons
    for each row execute function public.set_updated_at();

-- =====================================================================
-- VIEWS — reproduce the Airtable grids by resolving FKs (the anchors)
-- =====================================================================

-- helper: minutes a lesson runs (explicit value, else end-start)
-- (inlined in the views below via coalesce)

-- ----- LESSONS grid: every lookup column comes from the FK record -----
create or replace view public.lessons_full as
select
    l.id,
    l.lesson_id,
    l.date,
    l.start_time,
    l.end_time,
    l.teacher_id,
    l.course_id,
    l.status,
    l.role,
    coalesce(l.lesson_duration_minutes,
             (extract(epoch from (l.end_time - l.start_time)) / 60)::int) as lesson_duration_minutes,
    t.teacher_name             as teacher_name_from_teacher,
    t.email                    as teacher_email_from_teacher,
    t.tutor_rate               as tutor_hourly_rate,
    t.ta_rate                  as ta_hourly_rate,
    case when l.role = 'Teaching Assistant' then t.ta_rate else t.tutor_rate end as teacher_hourly_rate_based_on_role,
    l.miscellaneous_expenses,
    t.reliability_score        as reliability_score_from_teacher,
    c.course_name              as course_name_from_course,
    c.course_topic             as course_topic_from_course,
    round(
        coalesce(case when l.role = 'Teaching Assistant' then t.ta_rate else t.tutor_rate end, 0)
        * coalesce(l.lesson_duration_minutes,
                   (extract(epoch from (l.end_time - l.start_time)) / 60))::numeric / 60.0
    )                          as lesson_payout,
    l.tutor_assignment,
    l.offer_sent_timestamp,
    l.lesson_material_link,
    c.school_id,
    s.school_name,
    l.created_at,
    l.updated_at
from public.lessons l
left join public.teachers t on t.teacher_id = l.teacher_id
left join public.courses  c on c.course_id  = l.course_id
left join public.schools  s on s.school_id  = c.school_id;

-- ----- TEACHERS grid: rollups over the teacher's lessons -----
create or replace view public.teachers_full as
select
    t.*,
    agg.total_lessons_taught,
    agg.total_hours_taught,
    agg.last_lesson_date,
    (select string_agg(l.lesson_id, ', ' order by l.date)
       from public.lessons l where l.teacher_id = t.teacher_id and l.lesson_id is not null) as lessons
from public.teachers t
left join lateral (
    select count(*)                                       as total_lessons_taught,
           coalesce(sum(coalesce(l.lesson_duration_minutes,
                    (extract(epoch from (l.end_time - l.start_time)) / 60))), 0) / 60.0 as total_hours_taught,
           max(l.date)                                    as last_lesson_date
    from public.lessons l
    where l.teacher_id = t.teacher_id
) agg on true;

-- ----- COURSES grid: rollups over the course's lessons + school lookup -----
create or replace view public.courses_full as
select
    c.course_id,
    c.course_name,
    c.school_id,
    s.school_name as school_name_lookup,
    c.course_topic,
    c.course_types,
    c.revenue_per_lesson,
    c.scheduled_classes_ai_summary,
    agg.number_of_lessons,
    agg.total_hours,
    agg.first_lesson_date,
    agg.last_lesson_date,
    (coalesce(agg.number_of_lessons, 0) * coalesce(c.revenue_per_lesson, 0)) as total_revenue,
    agg.total_teacher_costs,
    case when (coalesce(agg.number_of_lessons, 0) * coalesce(c.revenue_per_lesson, 0)) > 0
         then round(100.0 * (
                (coalesce(agg.number_of_lessons, 0) * coalesce(c.revenue_per_lesson, 0)) - coalesce(agg.total_teacher_costs, 0)
              ) / (coalesce(agg.number_of_lessons, 0) * coalesce(c.revenue_per_lesson, 0)))
         else null end as profit_margin_pct,
    (select string_agg(l.lesson_id, ', ' order by l.date)
       from public.lessons l where l.course_id = c.course_id and l.lesson_id is not null) as lessons
from public.courses c
left join public.schools s on s.school_id = c.school_id
left join lateral (
    select count(*) as number_of_lessons,
           coalesce(sum(coalesce(l.lesson_duration_minutes,
                    (extract(epoch from (l.end_time - l.start_time)) / 60))), 0) / 60.0 as total_hours,
           min(l.date) as first_lesson_date,
           max(l.date) as last_lesson_date,
           coalesce(sum(
               round(coalesce(case when l.role = 'Teaching Assistant' then tt.ta_rate else tt.tutor_rate end, 0)
                     * coalesce(l.lesson_duration_minutes,
                               (extract(epoch from (l.end_time - l.start_time)) / 60))::numeric / 60.0)
           ), 0) as total_teacher_costs
    from public.lessons l
    left join public.teachers tt on tt.teacher_id = l.teacher_id
    where l.course_id = c.course_id
) agg on true;

-- ----- SCHOOLS grid: rollups over the school's courses/lessons -----
create or replace view public.schools_full as
select
    s.school_id,
    s.school_name,
    (select string_agg(c.course_id, ', ' order by c.course_id)
       from public.courses c where c.school_id = s.school_id) as courses,
    (select count(*) from public.courses c where c.school_id = s.school_id) as number_of_courses,
    coalesce((
        select sum(coalesce(l.lesson_duration_minutes,
                   (extract(epoch from (l.end_time - l.start_time)) / 60)))
        from public.lessons l join public.courses c on c.course_id = l.course_id
        where c.school_id = s.school_id
    ), 0) / 60.0 as total_course_hours,
    (select max(l.date)
        from public.lessons l join public.courses c on c.course_id = l.course_id
        where c.school_id = s.school_id) as last_lesson_date_all_courses,
    (select string_agg(distinct c.course_types, ', ')
       from public.courses c where c.school_id = s.school_id) as course_types_offered,
    s.tutor_availability_submissions,
    s.tutor_availability_slots
from public.schools s;

-- ----- lesson_schedule: stable interface for the Schedule UI (3 colours) -----
create or replace view public.lesson_schedule as
select
    l.id,
    l.lesson_id                as lesson_code,
    l.date                     as lesson_date,
    l.start_time,
    l.end_time,
    case
        when l.status ilike 'cancelled'  then 'cancelled'
        when l.status ilike 'completed'  then 'completed'
        when l.teacher_id is not null or l.tutor_assignment ilike 'Tutor assigned' then 'assigned'
        else 'unassigned'
    end                        as status,
    l.status                   as raw_status,
    l.tutor_assignment,
    l.role,
    l.lesson_material_link,
    l.notes,
    l.course_id,
    c.course_name,
    c.school_id,
    s.school_name,
    l.teacher_id               as assigned_teacher_id,
    t.teacher_name             as assigned_teacher_name,
    t.whatsapp_number          as assigned_teacher_phone,
    (l.date is not null and l.date <= (current_date + 7)) as within_a_week,
    case
        when l.status ilike 'cancelled' then 'grey'
        when l.status ilike 'completed' then 'blue'
        when (l.teacher_id is not null or l.tutor_assignment ilike 'Tutor assigned') then 'green'
        when l.date is not null and l.date <= (current_date + 7) then 'red'
        else 'yellow'
    end                        as color,
    l.created_at,
    l.updated_at
from public.lessons l
left join public.courses  c on c.course_id  = l.course_id
left join public.schools  s on s.school_id  = c.school_id
left join public.teachers t on t.teacher_id = l.teacher_id;

-- ----- urgent_news: within a week & needs attention -----
create or replace view public.urgent_news as
select
    ls.id              as lesson_id,
    ls.lesson_code,
    ls.course_name,
    ls.school_name,
    ls.lesson_date,
    ls.start_time,
    ls.status,
    ls.color,
    case when ls.status = 'unassigned' then 'unassigned'
         when ls.status = 'cancelled'  then 'cancelled'
         else 'attention' end as reason
from public.lesson_schedule ls
where ls.lesson_date is not null
  and ls.lesson_date <= (current_date + 7)
  and ls.status in ('unassigned', 'cancelled')
order by ls.lesson_date asc, ls.start_time asc;

-- ---------------------------------------------------------------------
-- RLS (secure tutor data) — backend uses the service_role key.
-- ---------------------------------------------------------------------
alter table public.schools             enable row level security;
alter table public.teachers            enable row level security;
alter table public.courses             enable row level security;
alter table public.lessons             enable row level security;
alter table public.lesson_tutor_offers enable row level security;
alter table public.lesson_events       enable row level security;
