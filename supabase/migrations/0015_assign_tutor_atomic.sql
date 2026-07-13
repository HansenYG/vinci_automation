-- =====================================================================
-- 0015_assign_tutor_atomic.sql
-- Atomic tutor assignment stored procedure.
-- Replaces the race-prone application-level capacity check in
-- scheduling.py assign_tutor() with a DB-level atomic operation.
-- =====================================================================

-- Atomically assign a tutor to a lesson if capacity permits.
-- Returns: { success: bool, message: string, assigned_count: int }
create or replace function public.assign_tutor_atomic(
    p_lesson_id uuid,
    p_teacher_id text,
    p_max_tutors int default 1
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    v_current_count int;
    v_already_assigned bool;
    v_existing_teacher_id text;
    v_result jsonb;
begin
    -- Lock the lesson row to prevent concurrent assignments
    perform 1 from public.lessons where id = p_lesson_id for update;

    -- Check if this teacher is already assigned
    select exists(
        select 1 from public.lesson_tutor_offers
        where lesson_id = p_lesson_id
          and teacher_id = p_teacher_id
          and offer_status = 'assigned'
    ) into v_already_assigned;

    if v_already_assigned then
        return jsonb_build_object(
            'success', false,
            'message', 'DUPLICATE: This tutor is already assigned to this lesson.',
            'assigned_count', 0
        );
    end if;

    -- Check existing assigned count
    select count(*)
    into v_current_count
    from public.lesson_tutor_offers
    where lesson_id = p_lesson_id
      and offer_status = 'assigned';

    if v_current_count >= p_max_tutors then
        return jsonb_build_object(
            'success', false,
            'message', format('FULL: This lesson is full — %s tutor(s) already assigned (max).', p_max_tutors),
            'assigned_count', v_current_count
        );
    end if;

    -- Check existing teacher assignment on lesson
    select teacher_id into v_existing_teacher_id
    from public.lessons
    where id = p_lesson_id;

    -- Atomic upsert: mark offer as assigned
    insert into public.lesson_tutor_offers (lesson_id, teacher_id, offer_status, responded_at)
    values (p_lesson_id, p_teacher_id, 'assigned', now())
    on conflict (lesson_id, teacher_id)
    do update set offer_status = 'assigned', responded_at = now();

    -- Re-count after assignment
    select count(*)
    into v_current_count
    from public.lesson_tutor_offers
    where lesson_id = p_lesson_id
      and offer_status = 'assigned';

    -- Update lesson status
    if v_current_count >= p_max_tutors then
        update public.lessons
        set status = 'Assigned',
            teacher_id = p_teacher_id,
            tutor_assignment = 'Tutor assigned'
        where id = p_lesson_id;
    else
        update public.lessons
        set teacher_id = p_teacher_id,
            tutor_assignment = 'Tutor assigned',
            status = case
                when coalesce(status, '') in ('Unassigned', 'OfferSent', '')
                then 'HasAcceptance'
                else status
            end
        where id = p_lesson_id;
    end if;

    return jsonb_build_object(
        'success', true,
        'message', 'assigned',
        'assigned_count', v_current_count,
        'max_tutors', p_max_tutors,
        'existing_teacher_id', v_existing_teacher_id
    );
end;
$$;
