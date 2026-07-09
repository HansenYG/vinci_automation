-- =====================================================================
-- Add "Number of tutors" (max assignable tutors) to lessons.
-- Also introduces an 'assigned' offer status so a lesson can hold several
-- assigned tutors (up to max_tutors), and surfaces both the cap and the
-- live assigned count in the lesson_schedule view.
-- =====================================================================

alter table public.lessons
    add column if not exists max_tutors integer not null default 1;

-- allow offer_status = 'assigned'
alter table public.lesson_tutor_offers
    drop constraint if exists lesson_tutor_offers_offer_status_check;
alter table public.lesson_tutor_offers
    add constraint lesson_tutor_offers_offer_status_check
    check (offer_status in ('pending', 'accepted', 'declined', 'withdrawn', 'assigned'));

-- urgent_news depends on lesson_schedule, so drop both and recreate.
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
    coalesce(l.school_name, s.school_name) as school_name,
    l.teacher_id               as assigned_teacher_id,
    t.teacher_name             as assigned_teacher_name,
    t.whatsapp_number          as assigned_teacher_phone,
    l.max_tutors,
    (select count(*) from public.lesson_tutor_offers o
        where o.lesson_id = l.id and o.offer_status = 'assigned') as assigned_count,
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
