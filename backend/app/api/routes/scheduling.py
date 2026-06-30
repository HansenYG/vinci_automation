"""Trigger endpoints for the Phase-1 automation.

These back the Lesson Dashboard buttons ("send urgent WhatsApp", "assign this
accepted tutor") and the hourly Render Cron Job (run-due-reminders).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from app.core.config import settings
from app.core.database import get_supabase
from app.schemas.requests import AnnounceLessonRequest, AssignRequest
from app.services import repos, scheduling, wati

router = APIRouter(prefix="/scheduling", tags=["scheduling"])


@router.post("/lessons/{lesson_id}/blast")
def blast(lesson_id: str, db: Client = Depends(get_supabase)):
    """Send the 'lesson needs a tutor' WhatsApp to the pool (or all tutors)."""
    try:
        return scheduling.blast_lesson(db, lesson_id, force_all=True)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.post("/run-due-reminders")
def run_due_reminders(token: str = Query(default=""), db: Client = Depends(get_supabase)):
    """Hourly sweep: re-blast pending tutors past the 24h interval.
    Protected by the same secret as the webhook (the Cron Job passes ?token=)."""
    if settings.WATI_WEBHOOK_SECRET and token != settings.WATI_WEBHOOK_SECRET:
        raise HTTPException(403, "bad token")
    return scheduling.run_due_reminders(db)


@router.get("/lessons/{lesson_id}/accepted")
def accepted_pool(lesson_id: str, db: Client = Depends(get_supabase)):
    """Tutors who accepted — the candidates the admin chooses from."""
    ids = repos.accepted_teacher_ids(db, lesson_id)
    return [repos.get_row(db, "teachers", tid) for tid in ids]


@router.post("/announce-lesson")
def announce_lesson(body: AnnounceLessonRequest, db: Client = Depends(get_supabase)):
    """Create a lesson and WhatsApp the tutors the LLM judges suitable."""
    return scheduling.announce_lesson(
        db,
        lesson_code=body.lesson_code,
        date=body.date,
        start_time=body.start_time,
        end_time=body.end_time,
        course=body.course,
        school=body.school,
        max_tutors=body.max_tutors,
        lesson_income=body.lesson_income,
    )


@router.post("/lessons/{lesson_id}/assign")
def assign(lesson_id: str, body: AssignRequest, db: Client = Depends(get_supabase)):
    """Assign an accepted tutor and (by default) send the material link."""
    try:
        return scheduling.assign_tutor(db, lesson_id, body.teacher_id, send_files=body.send_files)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.post("/lessons/{lesson_id}/send-confirmation")
def resend_confirmation(lesson_id: str, db: Client = Depends(get_supabase)):
    """Re-send the confirmation + material link to the already-assigned tutor."""
    lesson = repos.get_lesson_view(db, lesson_id)
    if not lesson:
        raise HTTPException(404, "lesson not found")
    teacher_id = lesson.get("assigned_teacher_id")
    if not teacher_id:
        raise HTTPException(400, "lesson has no assigned tutor")
    teacher = repos.get_row(db, "teachers", teacher_id)
    ctx = repos.lesson_wati_context(lesson)
    ctx["tutor_name"] = teacher.get("teacher_name", "")
    phone = wati.normalize_phone(teacher.get("whatsapp_number")) or settings.FALLBACK_WHATSAPP_HK
    result = wati.send_confirmation(phone, ctx)
    repos.log_event(db, lesson_id, teacher_id, "material_sent", {"ok": result["ok"], "resend": True})
    return {"lesson_id": lesson_id, "confirmation": result}
