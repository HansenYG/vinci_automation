-- =====================================================================
-- Add "Lesson Income" field to lessons — allows per-lesson revenue
-- tracking alongside the existing lesson_payout (teacher cost) so that
-- profit per lesson can be computed directly.
-- =====================================================================

alter table public.lessons
    add column if not exists lesson_income numeric(12, 2);

-- ---------------------------------------------------------------------
-- Rebuild lessons_full to include lesson_income
-- NOTE: dropped first because the new column is inserted mid-list, which
-- CREATE OR REPLACE VIEW cannot do (it may only append trailing columns).
-- Dependent views are dropped below and recreated afterwards.
-- ---------------------------------------------------------------------
drop view if exists public.urgent_news;
drop view if exists public.lesson_schedule;
drop view if exists public.lessons_full;

create view public.lessons_full as
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
    l.lesson_income,
    c.school_id,
    s.school_name,
    l.created_at,
    l.updated_at
from public.lessons l
left join public.teachers t on t.teacher_id = l.teacher_id
left join public.courses  c on c.course_id  = l.course_id
left join public.schools  s on s.school_id  = c.school_id;

-- ---------------------------------------------------------------------
-- Rebuild lesson_schedule to include lesson_income
-- ---------------------------------------------------------------------
drop view if exists public.urgent_news;
drop view if exists public.lesson_schedule;

create view public.lesson_schedule as
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
    l.max_tutors,
    (select count(*) from public.lesson_tutor_offers o
        where o.lesson_id = l.id and o.offer_status = 'assigned') as assigned_count,
    l.lesson_income,
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

create view public.urgent_news as
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
