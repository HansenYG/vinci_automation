-- Delete lessons with no course_id (orphan lessons that have no school or course).
-- These were created during testing/development and clutter the schedule.

delete from public.lesson_tutor_offers
where lesson_id in (select id from public.lessons where course_id is null);

delete from public.lesson_events
where lesson_id in (select id from public.lessons where course_id is null);

delete from public.lessons
where course_id is null;

-- Verify
select count(*) as remaining_orphans from public.lessons where course_id is null;