-- =====================================================================
-- 0019_fix_view_slot_fulfilment.sql
-- Fix lesson_schedule status/colour so they reflect SLOT FULFILMENT
-- (filled assigned-tutor slots vs max_tutors) instead of forcing
-- 'assigned'/green whenever lessons.teacher_id is non-null.
--
-- Background: handle_cancellation() now removes only the cancelling tutor
-- and keeps any remaining assigned tutor as lessons.teacher_id. Under the
-- old view logic ("teacher_id is not null -> assigned/green") a lesson with
-- an empty slot still rendered green. Effective filled slots are now:
--   count(offers with offer_status='assigned')
--   + 1 when a legacy primary tutor exists only via lessons.teacher_id
--     (or the row carries the legacy 'Tutor assigned' label with no offers)
-- =====================================================================

begin;

drop view if exists public.urgent_news cascade;
drop view if exists public.lesson_schedule cascade;

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
        when (
            (select count(*) from public.lesson_tutor_offers o
              where o.lesson_id = l.id and o.offer_status = 'assigned')
            + case
                when l.teacher_id is not null and not exists (
                    select 1 from public.lesson_tutor_offers o3
                    where o3.lesson_id = l.id
                      and o3.teacher_id = l.teacher_id
                      and o3.offer_status = 'assigned'
                ) then 1
                when l.teacher_id is null and l.tutor_assignment ilike 'Tutor assigned'
                  and not exists (
                    select 1 from public.lesson_tutor_offers o4
                    where o4.lesson_id = l.id and o4.offer_status = 'assigned'
                ) then 1
                else 0
              end
        ) >= l.max_tutors then 'assigned'
        when l.status ilike 'hasacceptance' then 'hasacceptance'
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
    coalesce(s.school_name, l.school_name) as school_name,
    s.google_maps_link,
    l.teacher_id               as assigned_teacher_id,
    t.teacher_name             as assigned_teacher_name,
    t.whatsapp_number          as assigned_teacher_phone,
    l.max_tutors,
    (select count(*) from public.lesson_tutor_offers o
        where o.lesson_id = l.id and o.offer_status = 'assigned') as assigned_count,
    (
        select string_agg(t2.teacher_name, ', ' order by t2.teacher_name)
        from public.lesson_tutor_offers o2
        join public.teachers t2 on t2.teacher_id = o2.teacher_id
        where o2.lesson_id = l.id and o2.offer_status = 'assigned'
    ) as assigned_tutor_names,
    l.lesson_income,
    (l.date is not null and l.date <= (current_date + 7)) as within_a_week,
    case
        when l.status ilike 'cancelled' then 'grey'
        when (
            (select count(*) from public.lesson_tutor_offers o
              where o.lesson_id = l.id and o.offer_status = 'assigned')
            + case
                when l.teacher_id is not null and not exists (
                    select 1 from public.lesson_tutor_offers o3
                    where o3.lesson_id = l.id
                      and o3.teacher_id = l.teacher_id
                      and o3.offer_status = 'assigned'
                ) then 1
                when l.teacher_id is null and l.tutor_assignment ilike 'Tutor assigned'
                  and not exists (
                    select 1 from public.lesson_tutor_offers o4
                    where o4.lesson_id = l.id and o4.offer_status = 'assigned'
                ) then 1
                else 0
              end
        ) >= l.max_tutors then 'green'
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
