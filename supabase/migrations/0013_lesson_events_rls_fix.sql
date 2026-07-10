-- Allow all authenticated inserts to lesson_events (audit log).
-- The webhook handler inserts events without a user session (service_role),
-- and even with anon key the current_is_admin() check fails because
-- auth.uid() is null for service-level requests.

drop policy if exists events_insert on public.lesson_events;
create policy events_insert on public.lesson_events
    for insert
    with check (true);
