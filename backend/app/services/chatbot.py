"""Chatbot service — the admin's natural-language interface to the database.

Routing:
  * If the LLM is reachable, it answers everything — grounded with a live
    DB snapshot (counts + upcoming / unassigned / urgent lessons) so it can both
    reason/summarise AND answer operational questions accurately.
  * If the LLM is down, fall back to deterministic DB answers (so the common
    operational queries still work offline), then a friendly offline message.

Data modification (reschedule, create, delete):
  When the user asks to modify data the LLM outputs a JSON action block which
  the backend surfaces to the frontend as a pendingAction.  The frontend asks
  the user to confirm before the backend executes it.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime

import httpx
from postgrest import SyncPostgrestClient

Client = SyncPostgrestClient

from app.core.config import settings
from app.services import repos, codes

SCHEDULE_VIEW = "lesson_schedule"

# Preset prompts surfaced as one-click buttons in the UI.
PRESETS = [
    {"id": "unassigned", "label": "Show unassigned lessons", "prompt": "List all unassigned lessons by date"},
    {"id": "today", "label": "Today's schedule", "prompt": "What lessons are on today?"},
    {"id": "urgent", "label": "Urgent (within a week)", "prompt": "Show urgent lessons within a week"},
    {"id": "summary", "label": "Summarise the schedule", "prompt": "Give me a short summary of the current schedule and anything that needs attention"},
    {"id": "export_lessons", "label": "Export lessons to Excel", "prompt": "Export all lessons to excel", "action": "export", "dataset": "lessons"},
]


def _counts(db: Client) -> dict[str, int]:
    def _count(table: str) -> int:
        return db.table(table).select("*", count="exact").limit(1).execute().count or 0
    return {
        "schools": _count("schools"),
        "teachers": _count("teachers"),
        "courses": _count("courses"),
        "lessons": _count("lessons"),
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

    if "unassigned" in m or "未分配" in m or "未安排" in m:
        rows = repos.list_unassigned(db, limit=50)
        lines = [f"- {r['lesson_code']} · {r.get('course_name') or '?'} · {r['lesson_date']} ({r['color']})" for r in rows]
        reply = f"{len(rows)} unassigned lesson(s):\n" + "\n".join(lines) if rows else "No unassigned lessons. 🎉"
        return {"reply": reply, "source": "db", "data": rows}

    if "urgent" in m or "within a week" in m or "緊急" in m or "急" in m:
        rows = db.table("urgent_news").select("*").execute().data or []
        lines = [f"- {r['lesson_code']} · {r.get('course_name') or '?'} · {r['lesson_date']} · {r['reason']}" for r in rows]
        reply = f"{len(rows)} urgent item(s):\n" + "\n".join(lines) if rows else "Nothing urgent within a week."
        return {"reply": reply, "source": "db", "data": rows}

    if "today" in m or "今日" in m:
        today = date.today().isoformat()
        rows = repos.list_schedule(db, today, today)
        lines = [f"- {r.get('start_time') or ''} {r.get('course_name') or '?'} · {r['status']}" for r in rows]
        label = "今日" if "今日" in m else "today"
        reply = f"{len(rows)} lesson(s) {label}:\n" + "\n".join(lines) if rows else f"No lessons scheduled {label}."
        return {"reply": reply, "source": "db", "data": rows}

    if any(w in m for w in ("how many", "count", "summary", "total", "總數", "統計", "幾多")):
        c = _counts(db)
        reply = f"Schools: {c['schools']}, Teachers: {c['teachers']}, Courses: {c['courses']}, Lessons: {c['lessons']}."
        return {"reply": reply, "source": "db", "data": c}

    return None


# --- LLM (primary when reachable) ------------------------------------------

def _llm_chat(
    messages: list[dict],
    *,
    temperature: float = 0.4,
    max_tokens: int = 4096,
    json_mode: bool = False,
) -> dict | None:
    """Call the configured LLM provider. Returns parsed JSON body on success, None on error."""
    provider = settings.LLM_PROVIDER
    base = settings.llm_base_url.rstrip("/")
    model = settings.llm_model
    timeout = settings.LLM_TIMEOUT_SECONDS

    try:
        if provider == "openai":
            headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}", "Content-Type": "application/json"}
            body: dict = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
            if json_mode:
                body["response_format"] = {"type": "json_object"}
            resp = httpx.post(f"{base}/chat/completions", json=body, headers=headers, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            return {"content": data["choices"][0]["message"]["content"].strip()}
        else:
            body = {"model": model, "messages": messages, "stream": False, "options": {"temperature": temperature, "num_predict": max_tokens}}
            if json_mode:
                body["format"] = "json"
            resp = httpx.post(f"{base}/api/chat", json=body, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            return {"content": data.get("message", {}).get("content", "").strip()}
    except Exception:
        return None


def _llm_reply(db: Client, message: str, history: list[dict]) -> dict:
    """Free-form answer via LLM, grounded with a live DB snapshot."""
    now = datetime.now()
    today = now.date().isoformat()
    day_name = now.strftime("%A")
    counts = _counts(db)

    upcoming = [
        _fmt(r) for r in
        db.table(SCHEDULE_VIEW).select(
            "lesson_code, lesson_date, start_time, course_name, status, assigned_teacher_name"
        ).gte("lesson_date", today).order("lesson_date").limit(8).execute().data or []
    ]

    unassigned_count = (
        db.table(SCHEDULE_VIEW).select("*", count="exact")
        .eq("status", "unassigned").limit(1).execute().count or 0
    )
    soonest_unassigned = [
        _fmt(r) for r in
        db.table(SCHEDULE_VIEW).select(
            "lesson_code, lesson_date, start_time, course_name, status, assigned_teacher_name"
        ).eq("status", "unassigned").order("lesson_date").limit(6).execute().data or []
    ]

    urgent_count = (
        db.table("urgent_news").select("*", count="exact").limit(1).execute().count or 0
    )
    urgent_items = [
        {"code": r.get("lesson_code"), "date": str(r.get("lesson_date") or ""), "reason": r.get("reason")}
        for r in (db.table("urgent_news").select("lesson_code, lesson_date, reason").limit(6).execute().data or [])
    ]

    system = (
        "You are the Vinci Automation admin assistant for a tutoring company. "
        "Be concise and direct. Reply in the same language as the user. "
        "Base every fact ONLY on the data snapshot below — "
        "if it isn't there, say you don't have that detail rather than guessing.\n\n"
        "You understand Cantonese (廣東話), Mandarin (普通話), and English. "
        "When the user speaks Cantonese or Chinese, reply in the same language. "
        "Parse Cantonese date/time terms using TODAY as reference:\n"
        "  今日/聽日/後日 = today/tomorrow/day-after-tomorrow\n"
        "  今個星期一/下個星期一 = this Monday / next Monday\n"
        "  上晝(am)/下晝(pm)/朝早(morning)/晏晝(afternoon)/夜晚(evening)\n"
        "  三點 = 3:00, 三點半 = 3:30, 三點九 = 3:45 (Cantonese traditional)\n"
        "  三個字 = 15 minutes (:15), 半個鐘 = 30 minutes\n"
        "Map these to YYYY-MM-DD and HH:MM in the ACTION JSON.\n\n"
        "DATE RULES: Use 2026 for all dates. Even if the date has already passed, still create the lesson "
        "(this is scheduling/admin data entry). Do NOT refuse to create past dates. "
        "Use TODAY below as reference.\n"
        "COURSE RULES: NEVER make up course_id or guess course_name. Copy the EXACT course name "
        "from the user's message verbatim. If no course name is given, omit it.\n"
        "SCHEDULE RULES FOR 改期/取消/改為:\n"
        "  - 取消 (cancelled): SKIP this date entirely. Do NOT include it.\n"
        "  - 改期X (rescheduled to X): SKIP the original date, ONLY include the new date X.\n"
        "    Example: 24/6改期29/6 → skip 24/6, include 29/6 only.\n"
        "  - 改為X (changed to X): SKIP the original date, ONLY include the new date X.\n"
        "    Example: 20/7改為21/7 → skip 20/7, include 21/7 only.\n"
        "  - Dates without any annotation: include them normally.\n"
        "  - CRITICAL: NEVER add dates that aren't explicitly listed. Only include dates the user mentioned.\n\n"
        "WHEN TO CREATE: Course name + dates = CREATE lessons. "
        "Even if the message doesn't say 'create' or 'add', a course name followed by date(s) means "
        "the user wants to schedule those lessons. ALWAYS output ACTION for this.\n"
        "HANDLE 另加 (additional sessions): When the user says 另加 or 加開, treat it as ADDITIONAL "
        "lessons in the same course. If different time slots are given, match each date with its "
        "nearest preceding time.\n\n"
        "You can RESCHEDULE, CREATE, CREATE_BATCH, ASSIGN, and DELETE lessons. "
        "ONLY output ACTION when the user asks to CREATE, RESCHEDULE, ASSIGN, or DELETE. "
        "For questions or queries, just reply normally without ACTION.\n"
        "ASSIGN keywords (Cantonese/Chinese): 安排, 分配, 指派, 教 (teach), assign\n"
        "When you do output ACTION, put it FIRST, "
        "then a BRIEF one-sentence explanation.\n"
        'ACTION:{"operation":"...","params":{...}}\n'
        'create: {"date":"YYYY-MM-DD","start_time":"HH:MM","end_time":"HH:MM","max_tutors":1}\n'
        'create_batch: {"lessons":[{"date":"...","start_time":"...","end_time":"..."},...],"max_tutors":1}\n'
        'reschedule: {"lesson_id":"...","date?":"...","start_time?":"...","end_time?":"..."}\n'
        'assign: {"lesson_id":"...","teacher_id":"..."} or {"lesson_id":"...","teacher_name":"..."}\n'
        'delete: {"lesson_id":"..."}\n'
        'Use "course_name" (not course_id) for create/create_batch.\n\n'
        "EXAMPLES (ACTION FIRST, then explanation):\n"
        'User: "Move IGCSE Physics lesson July 10 to 16:00"\n'
        'ACTION:{"operation":"reschedule","params":{"lesson_id":"L-2026-010","start_time":"16:00"}}\n'
        'I can reschedule that lesson. Shall I proceed?\n\n'
        'User: "Create drone lessons on 24/2 3:10-4:10pm and 17/3 3:10-4:10pm"\n'
        'ACTION:{"operation":"create_batch","params":{"lessons":[{"date":"2026-02-24","start_time":"15:10","end_time":"16:10"},{"date":"2026-03-17","start_time":"15:10","end_time":"16:10"}]}}\n'
        'I will create 2 drone lessons. Shall I proceed?\n\n'
        'User: "無人機小組上課日子 24/2, 17/3, 3:10-4:10"\n'
        'ACTION:{"operation":"create_batch","params":{"course_name":"無人機小組","lessons":[{"date":"2026-02-24","start_time":"15:10","end_time":"16:10"},{"date":"2026-03-17","start_time":"15:10","end_time":"16:10"}]}}\n'
        '我會創建2個課堂。開始嗎？\n\n'
        'User: "ICT Python course 24/6改期29/6, 6/7取消, 13/7, 20/7改為21/7"\n'
        'ACTION:{"operation":"create_batch","params":{"course_name":"ICT Python AI Advanced Course","lessons":[{"date":"2026-06-29","start_time":"14:30","end_time":"17:00"},{"date":"2026-07-13","start_time":"14:30","end_time":"17:00"},{"date":"2026-07-21","start_time":"14:30","end_time":"17:00"}]}}\n'
        'I will create 3 lessons. Shall I proceed?\n\n'
        'User: "Drone Course 10/3, 17/3, 24/3, 時間2-4pm 另加四月班：7/4, 14/4, 時間2:30-4:30"\n'
        'ACTION:{"operation":"create_batch","params":{"course_name":"Drone Course","lessons":[{"date":"2026-03-10","start_time":"14:00","end_time":"16:00"},{"date":"2026-03-17","start_time":"14:00","end_time":"16:00"},{"date":"2026-03-24","start_time":"14:00","end_time":"16:00"},{"date":"2026-04-07","start_time":"14:30","end_time":"16:30"},{"date":"2026-04-14","start_time":"14:30","end_time":"16:30"}]}}\n'
        'I will create 5 lessons. Shall I proceed?\n\n'
        'User: "Assign Alice Chan to ICT Python lesson 29/6"\n'
        'ACTION:{"operation":"assign","params":{"lesson_id":"L-2026-029","teacher_name":"Alice Chan"}}\n'
        'I will assign Alice Chan to that lesson. Shall I proceed?\n\n'
        'User: "how many lessons do I have?"\n'
        'You have 15 lessons in the schedule...\n\n'
         f"TODAY is {day_name} {today} (YYYY-MM-DD). "
        "Use this as your reference for 'today', 'tomorrow', 'yesterday', "
        "'next week', 'this week', 'next Monday', etc. "
        "When the user asks about a relative date, compute the exact date from this reference.\n"
        f"COUNTS: {counts}\n"
        f"UNASSIGNED lessons total={unassigned_count}, soonest: {soonest_unassigned}\n"
        f"URGENT (within a week) total={urgent_count}: {urgent_items}\n"
         f"UPCOMING lessons: {upcoming}\n"
        "CRITICAL: Any message with a course name + dates = create lessons. "
        "Do NOT just repeat/summarize the dates. Always output ACTION create_batch with those dates.\n"
    )
    full_messages = [{"role": "system", "content": system}]
    full_messages += [{"role": h.get("role", "user"), "content": h.get("content", "")} for h in history[-6:]]
    full_messages.append({"role": "user", "content": message})

    result = _llm_chat(full_messages)
    if result is not None:
        return {"reply": result["content"] or "(empty response)", "source": settings.LLM_PROVIDER}
    return {
        "reply": (
            "I can't reach the language model right now, but I can still answer "
            "operational questions like 'show unassigned lessons', 'urgent within a week', "
            "'today's schedule', or 'database summary' (also in 廣東話: 未分配/緊急/今日/總數). "
            "To add data, use the input forms."
        ),
        "source": "fallback",
    }


def answer(db: Client, message: str, history: list[dict] | None = None) -> dict:
    # LLM first (grounded). Only when it's unreachable do we use the
    # deterministic DB answers, then the offline message.
    res = _llm_reply(db, message, history or [])
    if res["source"] != "fallback":
        # Check for ACTION: JSON block in the reply
        reply = res.get("reply", "")
        action_match = re.search(r'^ACTION:\s*(\{.*)', reply, re.MULTILINE | re.DOTALL)
        if action_match:
            try:
                decoder = json.JSONDecoder()
                parsed, end_idx = decoder.raw_decode(action_match.group(1))
                clean_reply = reply[:action_match.start()].strip()
                trailing = action_match.group(1)[end_idx:].strip()
                if trailing:
                    clean_reply = (clean_reply + "\n" + trailing).strip()
                res["reply"] = clean_reply or "OK"
                res["pendingAction"] = parsed
            except (json.JSONDecodeError, ValueError):
                pass
        return res
    return _deterministic_answer(db, message) or res


# --- Execute pending actions (after user confirmation) -----------------------

def _resolve_lesson(db: Client, code_or_id: str, *, strict: bool = False) -> dict | None:
    """Resolve a lesson by UUID (id) or human-readable code (lesson_id).

    Args:
        db: Supabase client
        code_or_id: Lesson UUID or lesson_id code
        strict: If True, only allow exact matches (for destructive operations).
                If False, fall back to partial ilike match (for read/display).
    """
    try:
        uuid.UUID(code_or_id)
        rows = db.table("lessons").select("id, lesson_id").eq("id", code_or_id).limit(1).execute().data
        if rows:
            return rows[0]
    except (ValueError, AttributeError):
        pass
    rows = db.table("lessons").select("id, lesson_id").eq("lesson_id", code_or_id).limit(1).execute().data
    if rows:
        return rows[0]
    # For destructive operations, refuse partial matches
    if strict:
        return None
    rows = db.table("lessons").select("id, lesson_id").ilike("lesson_id", f"%{code_or_id}%").limit(1).execute().data
    return rows[0] if rows else None


def execute_operation(db: Client, operation: str, params: dict) -> dict:
    """Execute a user-confirmed data-modifying operation."""
    if operation == "reschedule":
        lesson_code = params.get("lesson_id")
        if not lesson_code:
            return {"ok": False, "error": "Missing lesson_id"}
        # Strict match required for destructive operations
        resolved = _resolve_lesson(db, lesson_code, strict=True)
        if not resolved:
            return {"ok": False, "error": f"Lesson {lesson_code} not found (exact match required)"}
        lesson_id = resolved["id"]
        updates = {}
        if params.get("date"): updates["date"] = params["date"]
        if params.get("start_time"): updates["start_time"] = params["start_time"]
        if params.get("end_time"): updates["end_time"] = params["end_time"]
        if not updates:
            return {"ok": False, "error": "No fields to update"}
        repos.update_row(db, "lessons", lesson_id, updates)
        return {"ok": True, "message": f"Lesson {lesson_code} updated."}

    if operation in ("create", "create_batch"):
        lessons = params.get("lessons", [])
        if not lessons:
            single = {k: params.get(k) for k in ("date", "start_time", "end_time") if params.get(k)}
            if single.get("date"):
                lessons = [dict(single)]
        if not lessons:
            return {"ok": False, "error": "Missing date(s)"}

        course_name = params.get("course_name")
        course_id = params.get("course_id")
        if course_name and not course_id:
            rows = db.table("courses").select("course_id").eq("course_name", course_name).limit(1).execute().data
            if rows:
                course_id = rows[0]["course_id"]

        created = []
        for les in lessons:
            les_date = les.get("date")
            les_start = les.get("start_time")
            les_end = les.get("end_time")
            les_code = codes.next_lesson_code(db, date=les_date, start_time=les_start, course_name=course_name)
            payload = {
                "date": les_date,
                "lesson_id": les_code,
                "status": "Unassigned",
                "max_tutors": params.get("max_tutors", 1),
            }
            if course_id:
                payload["course_id"] = course_id
            if les_start:
                payload["start_time"] = les_start
            if les_end:
                payload["end_time"] = les_end
            repos.insert_row(db, "lessons", payload)
            created.append(les_code)

        if len(created) == 1:
            return {"ok": True, "message": f"Lesson {created[0]} created."}
        return {"ok": True, "message": f"{len(created)} lessons created: {', '.join(created)}."}

    if operation == "assign":
        lesson_code = params.get("lesson_id")
        teacher_id = params.get("teacher_id")
        teacher_name = params.get("teacher_name")
        if not lesson_code:
            return {"ok": False, "error": "Missing lesson_id"}
        if not teacher_id and not teacher_name:
            return {"ok": False, "error": "Missing teacher_id or teacher_name"}
        if teacher_name and not teacher_id:
            rows = db.table("teachers").select("teacher_id").ilike("teacher_name", teacher_name.strip()).limit(1).execute().data
            if rows:
                teacher_id = rows[0]["teacher_id"]
            else:
                return {"ok": False, "error": f"Teacher '{teacher_name}' not found"}
        resolved = _resolve_lesson(db, lesson_code, strict=True)
        if not resolved:
            return {"ok": False, "error": f"Lesson {lesson_code} not found (exact match required)"}
        from app.services.scheduling import assign_tutor
        try:
            assign_tutor(db, resolved["id"], teacher_id, send_files=False)
            return {"ok": True, "message": f"Teacher assigned to {lesson_code}."}
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

    if operation == "delete":
        lesson_code = params.get("lesson_id")
        if not lesson_code:
            return {"ok": False, "error": "Missing lesson_id"}
        # Strict match required for destructive operations
        resolved = _resolve_lesson(db, lesson_code, strict=True)
        if not resolved:
            return {"ok": False, "error": f"Lesson {lesson_code} not found (exact match required)"}
        repos.delete_row(db, "lessons", resolved["id"])
        return {"ok": True, "message": f"Lesson {lesson_code} deleted."}

    return {"ok": False, "error": f"Unknown operation '{operation}'"}


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

    result = _llm_chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
        max_tokens=200,
        json_mode=True,
    )
    if result is not None:
        try:
            data = json.loads(result["content"])
            ids = [i for i in (data.get("teacher_ids") or []) if i in valid_ids]
            if ids:
                return ids[:limit], True
        except (json.JSONDecodeError, ValueError, KeyError):
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
