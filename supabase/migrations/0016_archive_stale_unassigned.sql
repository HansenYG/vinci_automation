-- =====================================================================
-- 0016_archive_stale_unassigned.sql
-- Archive lessons that have been in "Unassigned" status for more than
-- 30 days past their lesson_date. Moves them to "Archived" status so
-- they don't clutter the urgent feed or dashboard counts.
-- =====================================================================

create or replace function public.archive_stale_unassigned(max_age_days int default 30)
returns int
language plpgsql
security definer
set search_path = public
as $$
declare
    v_count int;
begin
    update public.lessons
    set status = 'Archived',
        notes = coalesce(notes, '') || ' | Auto-archived: stale unassigned lesson past ' || max_age_days || ' days'
    where status in ('Unassigned', 'OfferSent')
      and lesson_date < (current_date - max_age_days)
      and (notes is null or notes not like '%Auto-archived%');
    
    get diagnostics v_count = row_count;
    return v_count;
end;
$$;
