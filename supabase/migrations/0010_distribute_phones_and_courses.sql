-- Randomly assign 4 WhatsApp numbers to all tutors (round-robin by teacher_id)
-- Assign courses to lessons that are missing one.
-- Assign school_name to lessons that are missing one (from their course's school).
--
-- Run this in Supabase SQL editor for production, or via:
--   supabase db execute --file supabase/migrations/0010_distribute_phones_and_courses.sql

begin;

-- ── 1. Assign phones round-robin ──────────────────────────────────────────
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

-- ── 3. Ensure school_name column exists on lessons ──────────────────────
alter table public.lessons add column if not exists school_name text;

-- ── 4. Fill school_name from course → school for any lesson missing it ──
update public.lessons l
set school_name = s.school_name
from public.courses c
  join public.schools s on s.school_id = c.school_id
where l.course_id = c.course_id
  and (l.school_name is null or l.school_name = '');

commit;

-- Verify
select 'phones' as check, count(*) as updated from public.teachers
  where whatsapp_number in ('85294494304','85252408480','6281287776026','85297382471');

select 'orphan_fixed' as check, count(*) as remaining from public.lessons where course_id is null;

select 'school_filled' as check, count(*) as filled from public.lessons
  where school_name is not null and school_name != '';