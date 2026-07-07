"""Thin Supabase data-access helpers shared by routes, scheduling and webhooks.

Every function takes the Supabase ``Client`` so callers stay testable and the
service-role key (which bypasses RLS) lives only in the backend.
"""

from __future__ import annotations

import re
from typing import Any

from supabase import Client

SCHEDULE_VIEW = "lesson_schedule"

# Each table's primary-key column (natural keys mirror Airtable; lessons keep a
# surrogate uuid because many Airtable rows have a blank Lesson ID).
PKS = {
    "schools": "school_id",
    "teachers": "teacher_id",
    "courses": "course_id",
    "lessons": "id",
}


# --- generic table helpers -------------------------------------------------

def list_rows(db: Client, table: str, order: str | None = None) -> list[dict]:
    q = db.table(table).select("*")
    if order:
        q = q.order(order)
    return q.execute().data or []


def get_row(db: Client, table: str, row_id: str) -> dict | None:
    res = db.table(table).select("*").eq(PKS.get(table, "id"), row_id).limit(1).execute().data
    return res[0] if res else None


def insert_row(db: Client, table: str, payload: dict) -> dict:
    return db.table(table).insert(payload).execute().data[0]


def update_row(db: Client, table: str, row_id: str, payload: dict) -> dict | None:
    res = db.table(table).update(payload).eq(PKS.get(table, "id"), row_id).execute().data
    return res[0] if res else None


def delete_row(db: Client, table: str, row_id: str) -> bool:
    res = db.table(table).delete().eq(PKS.get(table, "id"), row_id).execute().data
    return len(res) > 0


# --- lessons / schedule ----------------------------------------------------

def list_schedule(
    db: Client,
    start: str | None = None,
    end: str | None = None,
    status: str | None = None,
    course_id: str | None = None,
    teacher_id: str | None = None,
) -> list[dict]:
    q = db.table(SCHEDULE_VIEW).select("*")
    if start:
        q = q.gte("lesson_date", start)
    if end:
        q = q.lte("lesson_date", end)
    if status:
        statuses = [s.strip().lower() for s in status.split(",") if s.strip()]
        if len(statuses) == 1:
            q = q.eq("status", statuses[0])
        elif statuses:
            q = q.in_("status", statuses)
    if course_id:
        q = q.eq("course_id", course_id)
    if teacher_id:
        q = q.eq("assigned_teacher_id", teacher_id)
    return q.order("lesson_date").order("start_time").execute().data or []


ACTION_NEEDED_STATUSES = ["unassigned", "offersent", "hasacceptance"]


def list_dashboard(
    db: Client,
    status: str | None = None,
    course_id: str | None = None,
    teacher_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 25,
    show_all: bool = False,
) -> dict:
    """
    Lesson Dashboard feed with pagination.

    Default behaviour (show_all=False, no status filter):
      Shows only action-needed lessons (unassigned, offersent, hasacceptance).
      Sorted per PRD urgency:
        Bucket 1 — no acceptances yet (unassigned / offersent): closest date first.
        Bucket 2 — has acceptances but not yet assigned (hasacceptance): closest date first.

    When a status filter is provided or show_all=True:
      Shows all matching lessons sorted by lesson_date ascending.

    Returns {items: [...], total: int, page: int, page_size: int, pages: int, counts: {...}}.
    """
    import math

    def _base_q():
        q = db.table(SCHEDULE_VIEW).select("*", count="exact")
        if date_from:
            q = q.gte("lesson_date", date_from)
        if date_to:
            q = q.lte("lesson_date", date_to)
        if course_id:
            q = q.eq("course_id", course_id)
        if teacher_id:
            q = q.eq("assigned_teacher_id", teacher_id)
        return q

    def _bulk_counts():
        """Compute unassigned_offersent, has_acceptance, and urgent counts
        with minimal data transfer (count header, no row data)."""
        def _c(**filters):
            q = db.table(SCHEDULE_VIEW).select("*", count="exact").limit(1)
            if date_from:
                q = q.gte("lesson_date", date_from)
            if date_to:
                q = q.lte("lesson_date", date_to)
            if course_id:
                q = q.eq("course_id", course_id)
            if teacher_id:
                q = q.eq("assigned_teacher_id", teacher_id)
            for k, v in filters.items():
                if isinstance(v, list):
                    q = q.in_(k, v)
                else:
                    q = q.eq(k, v)
            return q.execute().count or 0
        return {
            "unassigned_offersent": _c(status=["unassigned", "offersent"]),
            "has_acceptance": _c(status="hasacceptance"),
            "urgent": _c(status=["unassigned", "offersent", "hasacceptance"], within_a_week=True),
        }

    # ── Status filter path ──────────────────────────────────────────────
    if status:
        statuses = [s.strip().lower() for s in status.split(",") if s.strip()]
        q = _base_q()
        if len(statuses) == 1:
            q = q.eq("status", statuses[0])
        elif statuses:
            q = q.in_("status", statuses)
        q = q.order("lesson_date", desc=False).order("start_time", desc=False)
        offset = (page - 1) * page_size
        q = q.range(offset, offset + page_size - 1)
        res = q.execute()
        total = res.count or 0
        counts = _bulk_counts()
        counts["total"] = total
        pages = math.ceil(total / page_size) if page_size > 0 else 1
        return {"items": res.data or [], "total": total, "page": page, "page_size": page_size, "pages": pages, "counts": counts}

    # ── Show-all path ───────────────────────────────────────────────────
    if show_all:
        q = _base_q().order("lesson_date", desc=False).order("start_time", desc=False)
        offset = (page - 1) * page_size
        q = q.range(offset, offset + page_size - 1)
        res = q.execute()
        total = res.count or 0
        counts = _bulk_counts()
        counts["total"] = total
        pages = math.ceil(total / page_size) if page_size > 0 else 1
        return {"items": res.data or [], "total": total, "page": page, "page_size": page_size, "pages": pages, "counts": counts}

    # ── Default: action-needed only, two-bucket urgency sort (PRD §3.2) ─
    bucket1 = (
        _base_q()
        .in_("status", ["unassigned", "offersent"])
        .order("lesson_date", desc=False)
        .order("start_time", desc=False)
        .execute()
        .data or []
    )
    bucket2 = (
        _base_q()
        .eq("status", "hasacceptance")
        .order("lesson_date", desc=False)
        .order("start_time", desc=False)
        .execute()
        .data or []
    )

    all_items = bucket1 + bucket2
    total = len(all_items)
    pages = math.ceil(total / page_size) if page_size > 0 else 1
    offset = (page - 1) * page_size

    counts = {
        "total": total,
        "unassigned_offersent": len(bucket1),
        "has_acceptance": len(bucket2),
        "urgent": sum(1 for item in all_items if item.get("within_a_week")),
    }

    return {
        "items": all_items[offset: offset + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "counts": counts,
    }


def get_lesson_view(db: Client, lesson_id: str) -> dict | None:
    res = db.table(SCHEDULE_VIEW).select("*").eq("id", lesson_id).limit(1).execute().data
    return res[0] if res else None


def list_unassigned(db: Client, limit: int = 100) -> list[dict]:
    """Unassigned lessons, soonest first (Lesson Dashboard / reminder source)."""
    return (
        db.table(SCHEDULE_VIEW)
        .select("*")
        .eq("status", "unassigned")
        .order("lesson_date")
        .order("start_time")
        .limit(limit)
        .execute()
        .data
        or []
    )


def lesson_wati_context(view_row: dict) -> dict[str, str]:
    """Build the WATI param context from a lesson_schedule row."""
    from app.services.urgency import urgency_label

    return {
        "lesson_code": view_row.get("lesson_code") or "",
        "course_name": view_row.get("course_name") or "",
        "school_name": view_row.get("school_name") or "",
        "date": str(view_row.get("lesson_date") or ""),
        "start_time": str(view_row.get("start_time") or "")[:5],
        "end_time": str(view_row.get("end_time") or "")[:5],
        "urgency": urgency_label(view_row["lesson_date"]),
        "lesson_material_link": view_row.get("lesson_material_link") or "",
    }


# --- teachers --------------------------------------------------------------

def _digits(v: Any) -> str:
    return re.sub(r"\D", "", "" if v is None else str(v))


def teachers_by_phone(db: Client, phone: str) -> list[dict]:
    """All teachers whose WhatsApp number matches (tolerant of country-code
    differences). Several may share the two fallback test numbers."""
    target = _digits(phone)
    if not target:
        return []

    # Try exact match first (fast, uses DB index)
    rows = db.table("teachers").select("*").eq("whatsapp_number", target).execute().data or []
    if rows:
        return rows

    # Fallback: suffix match last 10 digits (handles country-code differences)
    suffix = target[-10:]
    if len(suffix) >= 8:
        rows = db.table("teachers").select("*").ilike("whatsapp_number", f"%{suffix}").execute().data or []
    return rows


def find_teacher_by_phone(db: Client, phone: str) -> dict | None:
    matches = teachers_by_phone(db, phone)
    return matches[0] if matches else None


# --- offer pool ------------------------------------------------------------

def get_offers(db: Client, lesson_id: str) -> list[dict]:
    return db.table("lesson_tutor_offers").select("*").eq("lesson_id", lesson_id).execute().data or []


def upsert_offer(db: Client, lesson_id: str, teacher_id: str, **fields) -> dict:
    payload = {"lesson_id": lesson_id, "teacher_id": teacher_id, **fields}
    return (
        db.table("lesson_tutor_offers")
        .upsert(payload, on_conflict="lesson_id,teacher_id")
        .execute()
        .data[0]
    )


def set_offer_status(db: Client, lesson_id: str, teacher_id: str, status: str, responded_at: str | None = None) -> None:
    payload: dict[str, Any] = {"offer_status": status}
    if responded_at:
        payload["responded_at"] = responded_at
    db.table("lesson_tutor_offers").update(payload).eq("lesson_id", lesson_id).eq("teacher_id", teacher_id).execute()


def offers_for_teacher(db: Client, teacher_id: str, status: str | None = None) -> list[dict]:
    q = db.table("lesson_tutor_offers").select("*").eq("teacher_id", teacher_id)
    if status:
        q = q.eq("offer_status", status)
    return q.execute().data or []


def assigned_lessons_for_teacher(db: Client, teacher_id: str) -> list[dict]:
    return (
        db.table(SCHEDULE_VIEW)
        .select("*")
        .eq("assigned_teacher_id", teacher_id)
        .order("lesson_date")
        .execute()
        .data
        or []
    )


def accepted_teacher_ids(db: Client, lesson_id: str) -> list[str]:
    rows = (
        db.table("lesson_tutor_offers")
        .select("teacher_id")
        .eq("lesson_id", lesson_id)
        .eq("offer_status", "accepted")
        .execute()
        .data
        or []
    )
    return [r["teacher_id"] for r in rows]


# --- audit log -------------------------------------------------------------

def log_event(db: Client, lesson_id: str | None, teacher_id: str | None, event_type: str, detail: dict | None = None) -> None:
    db.table("lesson_events").insert(
        {"lesson_id": lesson_id, "teacher_id": teacher_id, "event_type": event_type, "detail": detail or {}}
    ).execute()
