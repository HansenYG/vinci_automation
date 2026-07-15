"""Urgent News feed — surfaces lessons requiring immediate admin attention.

GET /api/urgent-news       — full list with context
GET /api/urgent-news/count — integer for sidebar badge
"""

from fastapi import APIRouter, Depends
from postgrest import SyncPostgrestClient

from app.api.deps import get_db
from app.services import repos

router = APIRouter(prefix="/urgent-news", tags=["urgent-news"])

# Reason descriptions shown to the admin
_REASON_TEXT = {
    "unassigned": "No tutor assigned — lesson needs a tutor within the week.",
    "cancelled": "Tutor cancelled — lesson needs a new tutor or reschedule.",
    "attention": "Needs attention — status requires review.",
}


def _enrich(rows: list[dict], db: SyncPostgrestClient) -> list[dict]:
    """Add human-readable descriptions and recent events to each row."""
    if not rows:
        return rows

    lesson_ids = [r["lesson_id"] for r in rows if r.get("lesson_id")]

    # Batch-fetch recent events for all urgent lessons
    events_by_lesson: dict[str, list[dict]] = {}
    if lesson_ids:
        try:
            all_events = (
                db.table("lesson_events")
                .select("lesson_id, event_type, teacher_id, detail, created_at")
                .in_("lesson_id", lesson_ids)
                .order("created_at", desc=True)
                .limit(50)
                .execute()
                .data or []
            )
            for ev in all_events:
                lid = ev.get("lesson_id")
                if lid:
                    events_by_lesson.setdefault(lid, []).append(ev)
        except Exception:
            pass  # Non-fatal — page still works without events

    # Batch-fetch teacher names for event teacher_ids
    teacher_ids = {
        ev.get("teacher_id")
        for evs in events_by_lesson.values()
        for ev in evs
        if ev.get("teacher_id")
    }
    teacher_names: dict[str, str] = {}
    if teacher_ids:
        try:
            teachers = repos.list_rows(db, "teachers")
            teacher_names = {t["teacher_id"]: t.get("teacher_name", t["teacher_id"]) for t in teachers if t.get("teacher_id") in teacher_ids}
        except Exception:
            pass

    for row in rows:
        reason = row.get("reason", "")
        row["reason_text"] = _REASON_TEXT.get(reason, "Requires attention.")

        # Attach recent events (max 3)
        lid = row.get("lesson_id")
        raw_events = events_by_lesson.get(lid, [])[:3]
        row["recent_events"] = []
        for ev in raw_events:
            tid = ev.get("teacher_id")
            row["recent_events"].append({
                "type": ev.get("event_type"),
                "teacher": teacher_names.get(tid, tid) if tid else None,
                "at": ev.get("created_at"),
            })

    return rows


@router.get("")
def urgent_news(db: SyncPostgrestClient = Depends(get_db)):
    rows = db.table("urgent_news").select("*").execute().data or []
    return _enrich(rows, db)


@router.get("/count")
def urgent_count(db: SyncPostgrestClient = Depends(get_db)):
    rows = db.table("urgent_news").select("lesson_id").execute().data or []
    return {"count": len(rows)}
