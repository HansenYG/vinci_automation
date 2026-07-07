"""Generate IDs / codes that follow the existing data's format, so the admin
never has to type them.

  teachers : TCH-### (next after the highest existing TCH-### )
  schools  : SCH###  (next after the highest existing SCH### )
  courses  : an acronym of the course name (e.g. "Advanced Robotics Workshop"
             -> "ARW"), de-duplicated with a trailing number if needed
  lessons  : LES-YYYYMMDD-HHMM-<course acronym>  (e.g. LES-20260622-0900-ARW)
"""

from __future__ import annotations

import re

from supabase import Client

from app.services import repos


def _max_seq(values, pattern: str) -> int:
    rx = re.compile(pattern)
    best = 0
    for v in values:
        m = rx.match(str(v or ""))
        if m:
            best = max(best, int(m.group(1)))
    return best


def _acronym(name: str | None) -> str:
    words = re.findall(r"[A-Za-z0-9]+", name or "")
    if not words:
        return "CRS"
    if len(words) == 1:
        return words[0][:4].upper()
    return "".join(w[0] for w in words).upper()


def next_teacher_id(db: Client) -> str:
    ids = [t.get("teacher_id") for t in repos.list_rows(db, "teachers")]
    n = _max_seq(ids, r"^TCH-(\d+)$") + 1
    return f"TCH-{n:03d}"


def next_school_id(db: Client) -> str:
    ids = [s.get("school_id") for s in repos.list_rows(db, "schools")]
    n = _max_seq(ids, r"^SCH(\d+)$") + 1
    return f"SCH{n:03d}"


def next_course_id(db: Client, name: str | None) -> str:
    existing = {c.get("course_id") for c in repos.list_rows(db, "courses")}
    base = _acronym(name)
    code, i = base, 2
    while code in existing:
        code, i = f"{base}{i}", i + 1
    return code


def next_lesson_code(db: Client, *, date, start_time, course_name: str | None = None) -> str:
    d = re.sub(r"\D", "", str(date or ""))[:8] or "00000000"
    hhmm = re.sub(r"\D", "", str(start_time or ""))[:4] or "0000"
    base = f"LES-{d}-{hhmm}-{_acronym(course_name)}"
    code = base
    i = 2
    while True:
        exists = db.table("lessons").select("id").eq("lesson_id", code).limit(1).execute().data
        if not exists:
            return code
        code, i = f"{base}-{i}", i + 1
