"""Chatbot service — the admin's natural-language interface to the database.

Routing:
  * If Ollama is reachable, the LLM answers everything — grounded with a live
    DB snapshot (counts + upcoming / unassigned / urgent lessons) so it can both
    reason/summarise AND answer operational questions accurately.
  * If Ollama is down, fall back to deterministic DB answers (so the common
    operational queries still work offline), then a friendly offline message.

Data *input* and bulk *export* are handled by the REST endpoints and export.py;
the chat layer points the admin at them.
"""

from __future__ import annotations

import json
from datetime import date

import httpx
from supabase import Client

from app.core.config import settings
from app.services import repos

# Preset prompts surfaced as one-click buttons in the UI.
PRESETS = [
    {"id": "unassigned", "label": "Show unassigned lessons", "prompt": "List all unassigned lessons by date"},
    {"id": "today", "label": "Today's schedule", "prompt": "What lessons are on today?"},
    {"id": "urgent", "label": "Urgent (within a week)", "prompt": "Show urgent lessons within a week"},
    {"id": "summary", "label": "Summarise the schedule", "prompt": "Give me a short summary of the current schedule and anything that needs attention"},
    {"id": "export_lessons", "label": "Export lessons to Excel", "prompt": "Export all lessons to excel", "action": "export", "dataset": "lessons"},
]


def _counts(db: Client) -> dict[str, int]:
    return {
        "schools": len(repos.list_rows(db, "schools")),
        "teachers": len(repos.list_rows(db, "teachers")),
        "courses": len(repos.list_rows(db, "courses")),
        "lessons": len(repos.list_rows(db, "lessons")),
    }


def _fmt(r: dict) -> dict:
    return {
        "code": r.get("lesson_code"),
        "date": str(r.get("lesson_date") or ""),
        "time": str(r.get("start_time") or "")[:5],
        "course": r.get("course_name"),
        "status": r.get("status"),
        "teacher": r.get("assigned_teacher_name"),
    }


# --- deterministic answers (used as the OFFLINE fallback) ------------------

def _deterministic_answer(db: Client, message: str) -> dict | None:
    m = message.lower()

    if "unassigned" in m:
        rows = repos.list_unassigned(db, limit=50)
        lines = [f"- {r['lesson_code']} · {r.get('course_name') or '?'} · {r['lesson_date']} ({r['color']})" for r in rows]
        reply = f"{len(rows)} unassigned lesson(s):\n" + "\n".join(lines) if rows else "No unassigned lessons. 🎉"
        return {"reply": reply, "source": "db", "data": rows}

    if "urgent" in m or "within a week" in m:
        rows = db.table("urgent_news").select("*").execute().data or []
        lines = [f"- {r['lesson_code']} · {r.get('course_name') or '?'} · {r['lesson_date']} · {r['reason']}" for r in rows]
        reply = f"{len(rows)} urgent item(s):\n" + "\n".join(lines) if rows else "Nothing urgent within a week."
        return {"reply": reply, "source": "db", "data": rows}

    if "today" in m:
        today = date.today().isoformat()
        rows = repos.list_schedule(db, today, today)
        lines = [f"- {r.get('start_time') or ''} {r.get('course_name') or '?'} · {r['status']}" for r in rows]
        reply = f"{len(rows)} lesson(s) today:\n" + "\n".join(lines) if rows else "No lessons scheduled today."
        return {"reply": reply, "source": "db", "data": rows}

    if any(w in m for w in ("how many", "count", "summary", "total")):
        c = _counts(db)
        reply = f"Schools: {c['schools']}, Teachers: {c['teachers']}, Courses: {c['courses']}, Lessons: {c['lessons']}."
        return {"reply": reply, "source": "db", "data": c}

    return None


# --- LLM (primary when reachable) ------------------------------------------

def _ollama_reply(db: Client, message: str, history: list[dict]) -> dict:
    """Free-form answer via Ollama, grounded with a live DB snapshot."""
    today = date.today().isoformat()
    counts = _counts(db)
    upcoming = [_fmt(r) for r in repos.list_schedule(db, today, None)[:12]]
    unassigned_all = repos.list_unassigned(db, 1000)
    urgent_all = db.table("urgent_news").select("*").execute().data or []

    system = (
        "You are the Vinci Automation admin assistant for a tutoring company. "
        "Be concise and helpful. Base every fact ONLY on the data snapshot below — "
        "if it isn't there, say you don't have that detail rather than guessing. "
        "To change data, tell the user to use the Data tab / input forms.\n\n"
        f"COUNTS: {counts}\n"
        f"UNASSIGNED lessons total={len(unassigned_all)}, soonest: {[_fmt(r) for r in unassigned_all[:12]]}\n"
        f"URGENT (within a week) total={len(urgent_all)}: "
        f"{[{'code': r.get('lesson_code'), 'date': str(r.get('lesson_date') or ''), 'reason': r.get('reason')} for r in urgent_all[:12]]}\n"
        f"UPCOMING lessons: {upcoming}\n"
    )
    messages = [{"role": "system", "content": system}]
    messages += [{"role": h.get("role", "user"), "content": h.get("content", "")} for h in history[-6:]]
    messages.append({"role": "user", "content": message})

    try:
        resp = httpx.post(
            f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat",
            json={
                "model": settings.OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.4, "num_predict": 400},
            },
            timeout=settings.OLLAMA_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        content = resp.json().get("message", {}).get("content", "").strip()
        return {"reply": content or "(empty response)", "source": "ollama"}
    except httpx.HTTPError:
        return {
            "reply": (
                "I can't reach the language model right now, but I can still answer "
                "operational questions like 'show unassigned lessons', 'urgent within a week', "
                "'today's schedule', or 'database summary'. To add data, use the input forms."
            ),
            "source": "fallback",
        }


def answer(db: Client, message: str, history: list[dict] | None = None) -> dict:
    # LLM first (grounded). Only when it's unreachable do we use the
    # deterministic DB answers, then the offline message.
    res = _ollama_reply(db, message, history or [])
    if res["source"] != "fallback":
        return res
    return _deterministic_answer(db, message) or res


def select_tutor_ids(db: Client, *, course: str, school: str, topic: str = "", limit: int = 6) -> tuple[list[str], bool]:
    """Ask the LLM which tutors best fit a lesson. Returns (teacher_ids, llm_used).

    Falls back to a keyword match (then the first few active tutors) if Ollama is
    down or returns nothing usable — so the feature still works offline.
    """
    teachers = repos.list_rows(db, "teachers")
    active = [t for t in teachers if (t.get("status") or "").strip().lower() == "active"] or teachers
    pool = active[:40]
    valid_ids = {t.get("teacher_id") for t in teachers}
    candidates = [
        {
            "id": t.get("teacher_id"),
            "name": t.get("teacher_name"),
            "can_teach": (t.get("courses_can_teach") or "")[:100],
            "background": (t.get("background") or "")[:100],
        }
        for t in pool
    ]

    system = (
        "You match tutors to a lesson. From the candidate list, choose the tutors best suited "
        f"to teach the given course. Reply with ONLY JSON: {{\"teacher_ids\": [...]}} — up to {limit} "
        "ids taken from the candidates. Prefer relevant background/can_teach; if nothing clearly "
        "matches, choose the most generally capable."
    )
    user = f"LESSON course={course!r} school={school!r} topic={topic!r}\nCANDIDATES: {candidates}"

    try:
        resp = httpx.post(
            f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat",
            json={
                "model": settings.OLLAMA_MODEL,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.2, "num_predict": 200},
            },
            timeout=settings.OLLAMA_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = json.loads(resp.json().get("message", {}).get("content", "{}"))
        ids = [i for i in (data.get("teacher_ids") or []) if i in valid_ids]
        if ids:
            return ids[:limit], True
    except (httpx.HTTPError, json.JSONDecodeError, ValueError, KeyError):
        pass

    kw = (course or "").strip().lower()
    matched = [
        t.get("teacher_id") for t in pool
        if kw and (kw in (t.get("courses_can_teach") or "").lower()
                   or kw in (t.get("background") or "").lower()
                   or kw in (t.get("teacher_name") or "").lower())
    ]
    if matched:
        return matched[:limit], False
    return [t.get("teacher_id") for t in pool[:limit]], False
