-- =====================================================================
-- 0019_urgent_news_full_columns.sql
-- Expand the urgent_news view to pass through ALL columns from
-- lesson_schedule so the LessonDetailDrawer can work without
-- additional fetches.
-- =====================================================================

begin;

drop view if exists public.urgent_news cascade;

create view public.urgent_news as
select
    ls.id,
    ls.id                as lesson_id,
    ls.lesson_code,
    ls.course_name,
    ls.school_name,
    ls.google_maps_link,
    ls.lesson_date,
    ls.start_time,
    ls.end_time,
    ls.status,
    ls.color,
    ls.raw_status,
    ls.tutor_assignment,
    ls.role,
    ls.lesson_material_link,
    ls.notes,
    ls.school_id,
    ls.assigned_teacher_id,
    ls.assigned_teacher_name,
    ls.assigned_teacher_phone,
    ls.max_tutors,
    ls.assigned_count,
    ls.assigned_tutor_names,
    ls.lesson_income,
    ls.within_a_week,
    ls.created_at,
    ls.updated_at,
    ls.course_id,
    case when ls.status = 'unassigned' then 'unassigned'
         when ls.status = 'cancelled'  then 'cancelled'
         else 'attention' end as reason
from public.lesson_schedule ls
where ls.lesson_date is not null
  and ls.lesson_date <= (current_date + 7)
  and ls.status in ('unassigned', 'cancelled')
order by ls.lesson_date asc, ls.start_time asc;

commit;
