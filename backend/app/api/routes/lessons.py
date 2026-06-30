from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from app.core.database import get_supabase
from app.schemas.requests import LessonCreate, LessonUpdate
from app.services import codes, repos

router = APIRouter(prefix="/lessons", tags=["lessons"])


@router.get("")
def list_lessons(
    start: str | None = Query(default=None, description="ISO date lower bound"),
    end: str | None = Query(default=None, description="ISO date upper bound"),
    status: str | None = Query(default=None, description="Filter by status (comma-separated)"),
    course_id: str | None = Query(default=None, description="Filter by course_id"),
    teacher_id: str | None = Query(default=None, description="Filter by assigned teacher_id"),
    db: Client = Depends(get_supabase),
):
    """Schedule feed (joined + colour). Supports status/course/teacher filters."""
    return repos.list_schedule(db, start, end, status=status, course_id=course_id, teacher_id=teacher_id)


@router.get("/dashboard")
def list_dashboard(
    status: str | None = Query(default=None, description="Comma-separated statuses, e.g. 'unassigned,offersent'"),
    course_id: str | None = Query(default=None),
    teacher_id: str | None = Query(default=None),
    date_from: str | None = Query(default=None, description="ISO date lower bound"),
    date_to: str | None = Query(default=None, description="ISO date upper bound"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Client = Depends(get_supabase),
):
    """
    Lesson Dashboard feed — all lessons sorted by urgency (closest date first).
    Supports filtering by status, course, teacher, and date range.
    Returns paginated results with total count.
    """
    return repos.list_dashboard(
        db,
        status=status,
        course_id=course_id,
        teacher_id=teacher_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.get("/unassigned")
def list_unassigned(limit: int = 100, db: Client = Depends(get_supabase)):
    """Unassigned lessons, soonest first — the Lesson Dashboard source."""
    return repos.list_unassigned(db, limit)


@router.post("", status_code=201)
def create_lesson(body: LessonCreate, db: Client = Depends(get_supabase)):
    payload = body.model_dump(mode="json", exclude_none=True)
    if not payload.get("lesson_id"):
        course = repos.get_row(db, "courses", payload["course_id"]) if payload.get("course_id") else None
        payload["lesson_id"] = codes.next_lesson_code(
            db, date=payload.get("date"), start_time=payload.get("start_time"),
            course_name=(course or {}).get("course_name"),
        )
    row = repos.insert_row(db, "lessons", payload)
    return repos.get_lesson_view(db, row["id"])


@router.get("/{lesson_id}")
def get_lesson(lesson_id: str, db: Client = Depends(get_supabase)):
    row = repos.get_lesson_view(db, lesson_id)
    if not row:
        raise HTTPException(404, "lesson not found")
    return row


@router.patch("/{lesson_id}")
def update_lesson(lesson_id: str, body: LessonUpdate, db: Client = Depends(get_supabase)):
    updated = repos.update_row(db, "lessons", lesson_id, body.model_dump(mode="json", exclude_none=True))
    if not updated:
        raise HTTPException(404, "lesson not found")
    return repos.get_lesson_view(db, lesson_id)


@router.delete("/{lesson_id}", status_code=204)
def delete_lesson(lesson_id: str, db: Client = Depends(get_supabase)):
    repos.delete_row(db, "lessons", lesson_id)


@router.get("/{lesson_id}/offers")
def lesson_offers(lesson_id: str, db: Client = Depends(get_supabase)):
    """The tutor pool for a lesson, each offer enriched with the teacher."""
    offers = repos.get_offers(db, lesson_id)
    for o in offers:
        o["teacher"] = repos.get_row(db, "teachers", o["teacher_id"])
    return offers
