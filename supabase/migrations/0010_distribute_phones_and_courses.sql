-- Randomly assign 4 WhatsApp numbers to all tutors (round-robin by teacher_id)
-- and assign courses to lessons that are missing one.
--
-- Run this in Supabase SQL editor for production, or via:
--   supabase db execute --file supabase/migrations/0010_distribute_phones_and_courses.sql

begin;

-- ── 1. Assign phones round-robin ─────────────────────────────────────────
with numbered as (
  select teacher_id,
         row_number() over (order by teacher_id) - 1 as rn
  from public.teachers
)
update public.teachers t
set whatsapp_number = case n.rn % 4
  when 0 then '85294494304'
  when 1 then '85252408480'
  when 2 then '6281287776026'
  when 3 then '85297382471'
end
from numbered n
where t.teacher_id = n.teacher_id;

-- ── 2. Assign courses to lessons without one ──────────────────────────────
with random_course as (
  select id,
         (select course_id from public.courses order by random() limit 1) as new_course
  from public.lessons
  where course_id is null
)
update public.lessons l
set course_id = rc.new_course
from random_course rc
where l.id = rc.id;

commit;

-- Verify
select 'phones' as check, count(*) as updated from public.teachers
  where whatsapp_number in ('85294494304','85252408480','6281287776026','85297382471');

select 'orphan_fixed' as check, count(*) as remaining from public.lessons where course_id is null;