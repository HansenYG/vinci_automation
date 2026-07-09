from fastapi import APIRouter, Depends, HTTPException, Query
from postgrest import SyncPostgrestClient

from app.api.deps import get_db
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
    db: SyncPostgrestClient = Depends(get_db),
):
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
    show_all: bool = Query(default=False, description="If true, show all lessons (not just action-needed)"),
    db: SyncPostgrestClient = Depends(get_db),
):
    return repos.list_dashboard(
        db,
        status=status,
        course_id=course_id,
        teacher_id=teacher_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
        show_all=show_all,
    )


@router.get("/unassigned")
def list_unassigned(limit: int = 100, db: SyncPostgrestClient = Depends(get_db)):
    return repos.list_unassigned(db, limit)


@router.post("", status_code=201)
def create_lesson(body: LessonCreate, db: SyncPostgrestClient = Depends(get_db)):
    payload = body.model_dump(mode="json", exclude_none=True)
    if not payload.get("lesson_id"):
        course = repos.get_row(db, "courses", payload["course_id"]) if payload.get("course_id") else None
        payload["lesson_id"] = codes.next_lesson_code(
            db, date=payload.get("date"), start_time=payload.get("start_time"),
            course_name=(course or {}).get("course_name"),
        )
    row = repos.insert_row(db, "lessons", payload)
    lesson_id = row.get("id") if row else None
    if not lesson_id:
        raise HTTPException(500, "Failed to create lesson")
    return repos.get_lesson_view(db, lesson_id)


@router.get("/{lesson_id}")
def get_lesson(lesson_id: str, db: SyncPostgrestClient = Depends(get_db)):
    row = repos.get_lesson_view(db, lesson_id)
    if not row:
        raise HTTPException(404, "lesson not found")
    return row


@router.patch("/{lesson_id}")
def update_lesson(lesson_id: str, body: LessonUpdate, db: SyncPostgrestClient = Depends(get_db)):
    updated = repos.update_row(db, "lessons", lesson_id, body.model_dump(mode="json", exclude_none=True))
    if not updated:
        raise HTTPException(404, "lesson not found")
    return repos.get_lesson_view(db, lesson_id)


@router.delete("/cleanup-orphans")
def cleanup_orphan_lessons(db: SyncPostgrestClient = Depends(get_db)):
    orphans = db.table("lessons").select("id").filter("course_id", "is", "null").execute()
    ids = [o["id"] for o in orphans.data]
    if not ids:
        return {"deleted": 0}
    for lid in ids:
        db.table("lesson_tutor_offers").filter("lesson_id", "eq", lid).delete().execute()
        db.table("lesson_events").filter("lesson_id", "eq", lid).delete().execute()
        db.table("lessons").filter("id", "eq", lid).delete().execute()
    return {"deleted": len(ids)}

@router.delete("/{lesson_id}", status_code=204)
def delete_lesson(lesson_id: str, db: SyncPostgrestClient = Depends(get_db)):
    repos.delete_row(db, "lessons", lesson_id)


@router.get("/{lesson_id}/offers")
def lesson_offers(lesson_id: str, db: SyncPostgrestClient = Depends(get_db)):
    offers = repos.get_offers(db, lesson_id)
    for o in offers:
        o["teacher"] = repos.get_row(db, "teachers", o["teacher_id"])
    return offers
