-- Add google_maps_link to schools and school_id to lesson_events

begin;

alter table public.schools add column if not exists google_maps_link text;

alter table public.lesson_events add column if not exists school_id text;

commit;
