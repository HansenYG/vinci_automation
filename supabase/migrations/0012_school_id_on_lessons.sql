-- Add school_id to lessons table so each lesson can directly reference a school.
-- Populate it from the course → school chain, then update the lesson_schedule
-- view to use coalesce(l.school_id, c.school_id).

begin;

-- ── 1. Add the column ────────────────────────────────────────────────────
alter table public.lessons add column if not exists school_id text;

-- ── 2. Populate school_id from course → school for every lesson ──────────
update public.lessons l
set school_id = c.school_id
from public.courses c
where l.course_id = c.course_id
  and c.school_id is not null
  and (l.school_id is null or l.school_id = '');

-- ── 3. Recreate the view so school_id uses the lesson-level value first ──
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
    coalesce(l.school_id, c.school_id) as school_id,
    coalesce(l.school_name, s.school_name) as school_name,
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
left join public.schools  s on s.school_id  = coalesce(l.school_id, c.school_id)
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

commit;

-- Verify
select count(*) as school_id_filled from public.lessons
  where school_id is not null and school_id != '';

select count(*) as still_null from public.lessons
  where school_id is null or school_id = '';
