from fastapi import APIRouter, Depends, HTTPException, Query
from postgrest import SyncPostgrestClient
from datetime import datetime, time as time_t
from typing import Optional
from pydantic import BaseModel

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


def _do_create_lesson(db, body: LessonCreate):
    """Shared logic: dump, code-gen, insert, return the view row."""
    payload = body.model_dump(mode="json", exclude_none=True)
    course = repos.get_row(db, "courses", payload["course_id"]) if payload.get("course_id") else None
    
    # Auto-generate school_id if school_name is provided and course doesn't have one
    if payload.get("school_name") and not payload.get("school_id"):
        schools = repos.list_rows(db, "schools")
        existing_school = next((s for s in schools if s["school_name"] == payload["school_name"]), None)
        if existing_school:
            payload["school_id"] = existing_school["school_id"]
        else:
            # Create new school with auto-generated school_id
            new_school = repos.insert_row(db, "schools", {"school_name": payload["school_name"]})
            if new_school:
                payload["school_id"] = new_school["school_id"]
    
    # If no school_id provided at all but course has one, use course's school
    if not payload.get("school_id") and course and course.get("school_id"):
        payload["school_id"] = course["school_id"]
    
    if not payload.get("lesson_id"):
        payload["lesson_id"] = codes.next_lesson_code(
            db, date=payload.get("date"), start_time=payload.get("start_time"),
            course_name=(course or {}).get("course_name"),
        )
    
    # Only resolve school_name from db if not provided in input
    if not payload.get("school_name") and course:
        schools = repos.list_rows(db, "schools")
        school = next((s for s in schools if s["school_id"] == course.get("school_id")), None)
        if school:
            payload["school_name"] = school["school_name"]
    
    row = repos.insert_row(db, "lessons", payload)
    lesson_id = row.get("id") if row else None
    if not lesson_id:
        raise HTTPException(500, "Failed to create lesson")
    return repos.get_lesson_view(db, lesson_id)


@router.post("", status_code=201)
def create_lesson(body: LessonCreate, db: SyncPostgrestClient = Depends(get_db)):
    return _do_create_lesson(db, body)


@router.post("/batch", status_code=201)
def create_lessons_batch(
    body: list[LessonCreate],
    db: SyncPostgrestClient = Depends(get_db),
):
    """Create multiple lessons in one request. Each entry can have a different
    date, time, or course. Returns all created view rows."""
    created = []
    errors = []
    for i, item in enumerate(body):
        try:
            view = _do_create_lesson(db, item)
            created.append(view)
        except Exception as exc:
            errors.append({"index": i, "date": str(item.date), "detail": str(exc)})
    return {"created": created, "errors": errors, "total": len(created), "failed": len(errors)}


class MultiLessonInput(BaseModel):
    """Semi-structured lesson input matching the sample format."""
    course_name: str
    dates_text: str  # Multi-line text with dates and notes
    default_start_time: str = "14:30"
    default_end_time: str = "17:00"
    location: str | None = None
    school_name: str | None = None
    lesson_material_link: str | None = None
    max_tutors: int = 1
    lesson_income: float | None = None


@router.post("/parse-and-create", status_code=201)
def parse_and_create_lessons(
    body: MultiLessonInput,
    db: SyncPostgrestClient = Depends(get_db),
):
    """Parse semi-structured lesson input and create multiple lessons.
    
    Expected format for dates_text:
    - Each line: DD/MM/YYYY(Weekday)(optional note in parentheses)
    - Examples:
      - "24/6/2026(星期三)(因中五級進行SBA考試,改期)"
      - "29/6/2026(星期一)(因APL交流團,取消)"
      - "21/7/2026(星期二) ( 14:30 -17:30)"  # custom time override
    """
    import re
    from datetime import datetime
    
    # Parse the course to get course_id
    course = None
    try:
        courses = repos.list_rows(db, "courses")
        for c in courses:
            if c.get("course_name") == body.course_name:
                course = c
                break
        
        if not course:
            # Try to find partial match
            for c in courses:
                if body.course_name.lower() in c.get("course_name", "").lower():
                    course = c
                    break
    except Exception as e:
        # If course lookup fails, continue without course
        pass
    
    course_id = course.get("course_id") if course else None
    
    # Parse dates from the text
    lesson_entries = []
    lines = body.dates_text.strip().split('\n')
    
    date_pattern = re.compile(r'(\d{1,2})/(\d{1,2})/(\d{4})')
    time_pattern = re.compile(r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Extract date
        date_match = date_pattern.search(line)
        if not date_match:
            continue
            
        day, month, year = date_match.groups()
        try:
            lesson_date = datetime(int(year), int(month), int(day)).date()
        except ValueError:
            continue
        
        # Extract notes (content in parentheses)
        notes = []
        note_pattern = re.compile(r'\(([^)]+)\)')
        for note_match in note_pattern.finditer(line):
            note_content = note_match.group(1).strip()
            # Check if it's a time override
            time_override = time_pattern.search(note_content)
            if time_override:
                # This is a time specification, not a note
                continue
            # Skip weekday patterns (星期一, 星期二, etc., Monday, Tuesday, etc.)
            if re.match(r'^(星期|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun)', note_content, re.IGNORECASE):
                continue
            if note_content:
                notes.append(note_content)
        
        # Check for custom time override
        time_override = time_pattern.search(line)
        if time_override:
            start_h, start_m, end_h, end_m = time_override.groups()
            start_time = f"{start_h.zfill(2)}:{start_m}"
            end_time = f"{end_h.zfill(2)}:{end_m}"
        else:
            start_time = body.default_start_time
            end_time = body.default_end_time
        
        # Check for cancellation in notes
        is_cancelled = any("取消" in note or "cancel" in note.lower() for note in notes)
        
        # Skip cancelled lessons
        if is_cancelled:
            continue
        
        # Create lesson entry
        lesson_entry = LessonCreate(
            date=lesson_date,
            start_time=start_time,
            end_time=end_time,
            course_id=course_id,
            school_name=body.school_name,
            lesson_material_link=body.lesson_material_link,
            max_tutors=body.max_tutors,
            lesson_income=body.lesson_income,
            notes=", ".join(notes) if notes else None,
            status="Unassigned"
        )
        lesson_entries.append(lesson_entry)
    
    # Create all lessons
    created = []
    errors = []
    
    for i, entry in enumerate(lesson_entries):
        try:
            view = _do_create_lesson(db, entry)
            created.append(view)
        except Exception as exc:
            errors.append({"index": i, "date": str(entry.date), "detail": str(exc)})
    
    return {
        "created": created,
        "errors": errors,
        "total": len(created),
        "failed": len(errors),
        "course_matched": course is not None,
        "course_id": course_id
    }


@router.get("/{lesson_id}")
def get_lesson(lesson_id: str, db: SyncPostgrestClient = Depends(get_db)):
    row = repos.get_lesson_view(db, lesson_id)
    if not row:
        raise HTTPException(404, "lesson not found")
    return row


@router.patch("/{lesson_id}")
def update_lesson(lesson_id: str, body: LessonUpdate, db: SyncPostgrestClient = Depends(get_db)):
    payload = body.model_dump(mode="json", exclude_none=True)
    
    # Resolve school_name -> school_id when school is being set
    if payload.get("school_name") and not payload.get("school_id"):
        schools = repos.list_rows(db, "schools")
        existing_school = next((s for s in schools if s["school_name"] == payload["school_name"]), None)
        if existing_school:
            payload["school_id"] = existing_school["school_id"]
    
    updated = repos.update_row(db, "lessons", lesson_id, payload)
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
