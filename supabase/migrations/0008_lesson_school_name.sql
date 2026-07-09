-- Add school_name column to lessons table so the API can store it directly.
-- Existing lessons already expose school_name via the lessons_full view
-- (course → school join).  This column just gives the raw insert path a place
-- to store the value.  Populate existing NULL rows from the view for consistency.

alter table public.lessons add column if not exists school_name text;

update public.lessons l
set school_name = v.school_name
from public.lessons_full v
where l.id = v.id
  and l.school_name is null
  and v.school_name is not null;