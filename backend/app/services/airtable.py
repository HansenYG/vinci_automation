"""Optional one-time migration: pull legacy tutor/lesson data out of Airtable
into Supabase. Reads the same base/tables the Apps Scripts used.

Run via: python -m scripts.migrate_airtable   (from the backend/ dir)
Requires AIRTABLE_API_KEY + AIRTABLE_BASE_ID in .env.
"""

from __future__ import annotations

import httpx
from supabase import Client

from app.core.config import settings
from app.services import repos


def _fetch_all(table: str) -> list[dict]:
    """Page through every record of an Airtable table."""
    if not settings.AIRTABLE_API_KEY or not settings.AIRTABLE_BASE_ID:
        raise RuntimeError("AIRTABLE_API_KEY and AIRTABLE_BASE_ID must be set.")

    url = f"https://api.airtable.com/v0/{settings.AIRTABLE_BASE_ID}/{table}"
    headers = {"Authorization": f"Bearer {settings.AIRTABLE_API_KEY}"}
    records: list[dict] = []
    offset: str | None = None
    with httpx.Client(timeout=30) as client:
        while True:
            params = {"offset": offset} if offset else {}
            data = client.get(url, headers=headers, params=params).json()
            records.extend(data.get("records", []))
            offset = data.get("offset")
            if not offset:
                break
    return records


def import_teachers(db: Client) -> int:
    """Upsert Airtable Teachers (Teacher Name / WhatsApp Number / Teacher ID)."""
    count = 0
    for rec in _fetch_all(settings.AIRTABLE_TEACHERS_TABLE):
        f = rec.get("fields", {})
        teacher_id = f.get("Teacher ID")
        if not teacher_id:
            continue
        payload = {
            "teacher_id": teacher_id,
            "teacher_name": f.get("Teacher Name"),
            "email": f.get("Email"),
            "whatsapp_number": str(f.get("WhatsApp Number", "")).replace("+", "").replace(" ", "") or None,
        }
        db.table("teachers").upsert(payload, on_conflict="teacher_id").execute()
        count += 1
    return count


def import_lessons(db: Client) -> int:
    """Upsert Airtable Lessons by Lesson ID (course/teacher links left for review)."""
    count = 0
    for rec in _fetch_all(settings.AIRTABLE_LESSONS_TABLE):
        f = rec.get("fields", {})
        code = f.get("Lesson ID")
        if not code:
            continue
        payload = {"lesson_id": code}
        if f.get("Date"):
            payload["date"] = str(f["Date"])[:10]
        db.table("lessons").insert(payload).execute()
        count += 1
    return count


def run_migration(db: Client) -> dict:
    return {"teachers": import_teachers(db), "lessons": import_lessons(db)}


# convenience for ad-hoc use
def _default_client() -> Client:
    from app.core.database import get_supabase

    return get_supabase()
