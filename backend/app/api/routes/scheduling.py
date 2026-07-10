"""Trigger endpoints for the Phase-1 automation.

These back the Lesson Dashboard buttons ("send urgent WhatsApp", "assign this
accepted tutor") and the hourly Render Cron Job (run-due-reminders).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from postgrest import SyncPostgrestClient

from app.api.deps import get_db
from app.core.config import settings
from app.core.database import get_supabase
from app.schemas.requests import AnnounceLessonRequest, AssignRequest
from app.services import repos, scheduling, wati

router = APIRouter(prefix="/scheduling", tags=["scheduling"])


@router.post("/lessons/{lesson_id}/blast")
def blast(lesson_id: str, db: SyncPostgrestClient = Depends(get_db)):
    try:
        return scheduling.blast_lesson(db, lesson_id, force_all=True)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.post("/run-due-reminders")
def run_due_reminders(token: str = Query(default=""), db: SyncPostgrestClient = Depends(get_supabase)):
    if settings.WATI_WEBHOOK_SECRET and token != settings.WATI_WEBHOOK_SECRET:
        raise HTTPException(403, "bad token")
    return scheduling.run_due_reminders(db)


@router.get("/lessons/{lesson_id}/accepted")
def accepted_pool(lesson_id: str, db: SyncPostgrestClient = Depends(get_db)):
    ids = repos.accepted_teacher_ids(db, lesson_id)
    teachers = [t for t in (repos.get_row(db, "teachers", tid) for tid in ids) if t]
    teachers.sort(key=lambda t: (t.get("reliability_score") or 0), reverse=True)
    return teachers


@router.post("/announce-lesson")
def announce_lesson(body: AnnounceLessonRequest, db: SyncPostgrestClient = Depends(get_db)):
    school_id = None
    school_name = None

    # Resolve course_id either from body.course_id or by matching body.course
    course_id = body.course_id
    course_name = body.course or ""
    if not course_id and body.course:
        rows = db.table("courses").select("*").ilike("course_name", f"%{body.course}%").limit(1).execute().data or []
        if not rows:
            rows = db.table("courses").select("*").eq("course_id", body.course).limit(1).execute().data or []
        if rows:
            course_id = rows[0]["course_id"]
            course_name = rows[0].get("course_name") or body.course
    
    if body.school:
        schools = repos.list_rows(db, "schools")
        school = next((s for s in schools if s["school_name"] == body.school), None)
        if school:
            school_id = school["school_id"]
            school_name = school["school_name"]
        else:
            new_school = repos.insert_row(db, "schools", {"school_name": body.school})
            if new_school:
                school_id = new_school["school_id"]
                school_name = new_school["school_name"]
    
    return scheduling.announce_lesson(
        db,
        lesson_code=body.lesson_code,
        date=body.date,
        start_time=body.start_time,
        end_time=body.end_time,
        course=course_name,
        course_id=course_id,
        school=school_name,
        max_tutors=body.max_tutors,
        lesson_income=body.lesson_income,
        school_id=school_id,
    )


@router.post("/lessons/{lesson_id}/assign")
def assign(lesson_id: str, body: AssignRequest, db: SyncPostgrestClient = Depends(get_db)):
    from fastapi.responses import JSONResponse
    try:
        return scheduling.assign_tutor(
            db, lesson_id, body.teacher_id,
            send_files=body.send_files,
            force_reassign=body.force_reassign,
        )
    except ValueError as exc:
        msg = str(exc)
        if msg.startswith("DUPLICATE:"):
            return JSONResponse(status_code=409, content={"error_code": "DUPLICATE", "detail": msg[10:].strip()})
        if msg.startswith("CLASH:"):
            return JSONResponse(status_code=409, content={"error_code": "CLASH", "detail": msg[6:].strip()})
        if msg.startswith("FULL:"):
            return JSONResponse(status_code=409, content={"error_code": "FULL", "detail": msg[5:].strip()})
        raise HTTPException(400, msg)


@router.post("/lessons/{lesson_id}/send-confirmation")
def resend_confirmation(lesson_id: str, db: SyncPostgrestClient = Depends(get_db)):
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
