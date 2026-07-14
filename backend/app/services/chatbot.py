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
from difflib import get_close_matches
from datetime import date, datetime
from functools import lru_cache
import hashlib
from zoneinfo import ZoneInfo

from app.services import codes, repos

import httpx
from supabase import Client

from app.core.config import settings
from app.services import repos, codes
from app.services.translator import has_chinese, to_english, from_english, batch_to_english

# Simple in-memory cache for repeated queries (cache up to 100 most recent queries)
_RESPONSE_CACHE = {}
_CACHE_MAX_SIZE = 100

# Preset prompts surfaced as one-click buttons in the UI.
PRESETS = [
    {"id": "unassigned", "label": "Show unassigned lessons", "prompt": "List all unassigned lessons by date"},
    {"id": "today", "label": "Today's schedule", "prompt": "What lessons are on today?"},
    {"id": "urgent", "label": "Urgent (within a week)", "prompt": "Show urgent lessons within a week"},
    {"id": "summary", "label": "Summarise the schedule", "prompt": "Give me a short summary of the current schedule and anything that needs attention"},
    {"id": "export_lessons", "label": "Export lessons to Excel", "prompt": "Export all lessons to excel", "action": "export", "dataset": "lessons"},
]


def _tz_now() -> datetime:
    """Current datetime in configured timezone."""
    return datetime.now(ZoneInfo(settings.TIMEZONE))

def _tz_today() -> date:
    """Current date in configured timezone."""
    return _tz_now().date()

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


# --- deterministic answers (used as FAST rule-based responses) ------------------

def _deterministic_answer(db: Client, message: str) -> dict | None:
    """Fast rule-based responses for common queries - instant database queries."""
    m = message.lower()

    # Common keywords for quick rule-based responses
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
        today = _tz_today().isoformat()
        rows = repos.list_schedule(db, today, today)
        lines = [f"- {r.get('start_time') or ''} {r.get('course_name') or '?'} · {r['status']}" for r in rows]
        reply = f"{len(rows)} lesson(s) today:\n" + "\n".join(lines) if rows else "No lessons scheduled today."
        return {"reply": reply, "source": "db", "data": rows}

    if any(w in m for w in ("how many", "count", "summary", "total")):
        c = _counts(db)
        reply = f"Schools: {c['schools']}, Teachers: {c['teachers']}, Courses: {c['courses']}, Lessons: {c['lessons']}."
        return {"reply": reply, "source": "db", "data": c}

    # Quick responses for common data requests
    if "list all teachers" in m or "show teachers" in m:
        rows = repos.list_rows(db, "teachers", limit=50)
        lines = [f"- {r['teacher_name']} ({r['teacher_id']})" for r in rows]
        reply = f"{len(rows)} teacher(s):\n" + "\n".join(lines) if rows else "No teachers found."
        return {"reply": reply, "source": "db", "data": rows}

    if "list all courses" in m or "show courses" in m:
        rows = repos.list_rows(db, "courses", limit=50)
        lines = [f"- {r['course_name']} ({r['course_id']})" for r in rows]
        reply = f"{len(rows)} course(s):\n" + "\n".join(lines) if rows else "No courses found."
        return {"reply": reply, "source": "db", "data": rows}

    if "list all schools" in m or "show schools" in m:
        rows = repos.list_rows(db, "schools", limit=50)
        lines = [f"- {r['school_name']} ({r['school_id']})" for r in rows]
        reply = f"{len(rows)} school(s):\n" + "\n".join(lines) if rows else "No schools found."
        return {"reply": reply, "source": "db", "data": rows}

    return None


# --- LLM (primary when reachable) ------------------------------------------

def _llm_chat(
    messages: list[dict],
    *,
    temperature: float = 0.4,
    max_tokens: int = 250,
    json_mode: bool = False,
) -> dict | None:
    """Call the configured LLM provider. Returns parsed JSON body on success, None on error."""
    provider = settings.LLM_PROVIDER
    base = settings.llm_base_url.rstrip("/")
    model = settings.llm_model
    timeout = settings.LLM_TIMEOUT_SECONDS

    try:
        if provider == "groq":
            headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}", "Content-Type": "application/json"}
            body = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
            if json_mode:
                body["response_format"] = {"type": "json_object"}
            resp = httpx.post(f"{base}/chat/completions", json=body, headers=headers, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            return {"content": data["choices"][0]["message"]["content"].strip()}
        elif provider == "openai":
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


def _fuzzy_resolve_names(message: str, db: Client) -> tuple[str | None, str | None]:
    """Try to extract and resolve school/course names from user message via fuzzy match."""
    school_id, course_id = None, None
    # Extract school names from DB
    schools = db.table("schools").select("school_id,school_name").execute().data or []
    for s in schools:
        name = s.get("school_name", "")
        if not name:
            continue
        # Check if the name (or any word in it) appears in the message
        if name in message:
            school_id = s["school_id"]
            break
        # Fuzzy match for longer names (e.g. "你好" in "create lesson at 你好")
        words = name.split()
        if len(words) > 1:
            for w in words:
                if len(w) >= 2 and w in message:
                    school_id = s["school_id"]
                    break
        if school_id:
            break
    # Extract course names from DB
    courses = db.table("courses").select("course_id,course_name").execute().data or []
    for c in courses:
        name = c.get("course_name", "")
        if not name:
            continue
        if name in message:
            course_id = c["course_id"]
            break
        # Try matching significant words (3+ chars)
        for word in name.split():
            if len(word) >= 3 and word in message:
                course_id = c["course_id"]
                break
        if course_id:
            break
    return school_id, course_id


def _llm_reply(db: Client, message: str, history: list[dict], *, lang: bool = False,
               resolved_school_id: str | None = None,
               resolved_course_id: str | None = None) -> dict:
    """Free-form answer via LLM, grounded with a live DB snapshot."""
    now = _tz_now()
    today = now.date().isoformat()
    day_name = now.strftime("%A")   # e.g. "Wednesday"
    counts = _counts(db)
    upcoming = [_fmt(r) for r in repos.list_schedule(db, today, None)[:6]]
    courses_all = repos.list_rows(db, "courses")
    if lang:
        cn_course_names = [c.get('course_name') or '' for c in courses_all]
        eng_course_names = batch_to_english(cn_course_names)
        course_catalog = []
        for i, c in enumerate(courses_all):
            cn = cn_course_names[i]
            if not cn:
                continue
            en = eng_course_names[i]
            label = f"{cn} ({en})" if en.lower() != cn.lower() else cn
            course_catalog.append(f"{c['course_id']}: {label}")
    else:
        course_catalog = [f"{c['course_id']}: {c['course_name']}" for c in courses_all if c.get("course_name")]
    schools_all = repos.list_rows(db, "schools")
    if lang:
        cn_names = [s.get('school_name') or '' for s in schools_all]
        eng_names = batch_to_english(cn_names)
        school_catalog = []
        for i, s in enumerate(schools_all):
            cn = cn_names[i]
            if not cn:
                continue
            en = eng_names[i]
            label = f"{cn} ({en})" if en.lower() != cn.lower() else cn
            school_catalog.append(f"{s['school_id']}: {label}")
    else:
        school_catalog = [f"{s['school_id']}: {s['school_name']}" for s in schools_all if s.get("school_name")]
    unassigned_all = repos.list_unassigned(db, 100)
    urgent_all = db.table("urgent_news").select("*").execute().data or []

    system = (
        "You are the Vinci Automation admin assistant for a tutoring company. "
        "You understand Cantonese (廣東話), Mandarin (普通話), and English. "
        "Be concise and direct. Base every fact ONLY on the data snapshot below — "
        "if it isn't there, say you don't have that detail rather than guessing.\n\n"
        "Parse Cantonese date/time terms using TODAY as reference:\n"
        "  今日/聽日/後日 = today/tomorrow/day-after-tomorrow\n"
        "  上晝(am)/下晝(pm)/朝早(morning)/晏晝(afternoon)/夜晚(evening)\n"
        "  三點 = 3:00, 三點半 = 3:30, 三點九 = 3:45 (Cantonese traditional)\n\n"
        "DATE RULES: Use 2026 for all dates. Even if the date has already passed, still create the lesson "
        "(this is scheduling/admin data entry). Do NOT refuse to create past dates.\n"
        "SCHEDULE RULES FOR 改期/取消/改為:\n"
        "  - 取消 (cancelled): SKIP this date entirely.\n"
        "  - 改期X (rescheduled to X): SKIP the original date, ONLY include the new date X.\n"
        "  - 改為X (changed to X): SKIP the original date, ONLY include the new date X.\n"
        "  - Dates without any annotation: include them normally.\n\n"
        "CLARIFY INTENT FIRST: When a user provides dates/times for a course but does NOT explicitly "
        "say 'create', 'add', 'new', 'reschedule', 'move', 'change', or 'update', do NOT immediately "
        "output an ACTION. Instead, ask the user whether they want to:\n"
        "  1. Create new lessons for these dates\n"
        "  2. Reschedule/update existing lessons\n"
        "Wait for their response before outputting any ACTION block.\n\n"
        "ONLY output ACTION immediately when the user EXPLICITLY states their intent "
        "(e.g., 'create', 'add', 'new lesson', 'reschedule', 'move', 'delete', 'update').\n\n"
        "SCHOOL IS MANDATORY: Every lesson belongs to a school (our client). "
        "When creating a lesson, you MUST include school_name in the params. "
        "If the user does not mention a school, ASK them which school before outputting any ACTION.\n\n"
        "NON-EXISTENT COURSE HANDLING:\n"
        "Before creating a lesson, ALWAYS verify the course_name exists in the COURSE CATALOG below.\n"
        "Course catalog entries may appear as 'COURSE_ID: Chinese Name (English Translation)'. "
        "Match the user's course name against EITHER the Chinese name OR the English translation in parentheses.\n"
        "If the course does NOT exist in the catalog:\n"
        "  1. Do NOT output any ACTION for creating lessons.\n"
        "  2. Tell the user: \"The course '[name]' doesn't exist in our system. "
        "Would you like me to create it first?\"\n"
        "  3. If the user confirms, output:\n"
        '     ACTION:{"operation":"create_course","params":{"course_name":"...", "school_name":"..."}}\n'
        "     (Include optional fields like course_topic, course_types if the user mentioned them.)\n"
        "  4. After the course has been created (the user will say so in the next turn), "
        "ask if they still want to create the lesson.\n\n"
        "NON-EXISTENT SCHOOL HANDLING:\n"
        "ALWAYS check the SCHOOL CATALOG below when a user mentions a school by name.\n"
        "School catalog entries may appear as 'SCHOOL_ID: Chinese Name (English Translation)'. "
        "Match the user's school name against EITHER the Chinese name OR the English translation in parentheses.\n"
        "If the school does NOT exist in the catalog:\n"
        "  1. Do NOT output any ACTION that references the school.\n"
        "  2. Tell the user: \"The school '[name]' doesn't exist in our system. "
        "Would you like me to create it first?\"\n"
        "  3. If the user confirms, output:\n"
        '     ACTION:{"operation":"create_school","params":{"school_name":"..."}}\n'
        "  4. After the school has been created (the user will say so in the next turn), "
        "ask if they still want to proceed with the original request.\n\n"
        "You can RESCHEDULE, UPDATE, CREATE, DELETE lessons, and CREATE COURSES and CREATE SCHOOLS. "
        "When the user asks you to modify data, FIRST explain what you will do, "
        "then output an EXACT JSON block on its own line like this:\n"
        'ACTION:{"operation":"reschedule|update|create|delete|create_course|create_school","params":{...}}\n'
        "The JSON must contain:\n"
        '  - For "reschedule": {"lesson_id":"...", "date":"YYYY-MM-DD" (optional), "start_time":"HH:MM" (optional), "end_time":"HH:MM" (optional)}\n'
        '  - For "update": {"lesson_id":"...", ANY fields to change as flat keys. Examples: {"lesson_id":"L-2026-010","status":"Cancelled"} or {"lesson_id":"L-2026-010","course":"Advanced Robotics Workshop"} or {"lesson_id":"L-2026-010","notes":"Parent requested afternoon"} or {"lesson_id":"L-2026-010","start_time":"16:00","end_time":"17:30"} or {"lesson_id":"L-2026-010","school_name":"St. Mary\'s School"}}\n'
        '  - For "create": use "course_name" AND "school_name". If the user message includes "(school_id: ...)" or "(course_id: ...)", include them as "school_id" and "course_id" in the params too. Example: {"course_name":"IGCSE Physics","school_name":"St. Mary\'s School","school_id":"SCH-001","date":"YYYY-MM-DD","start_time":"HH:MM","end_time":"HH:MM","max_tutors":1}\n'
        '  - For "create_course": {"course_name":"...", "school_name":"...", "course_topic":"..." (optional), "course_types":"..." (optional)}\n'
        '  - For "create_school": {"school_name":"..."}\n'
        '  - For "delete": {"lesson_id":"..."}\n'
        "Do NOT execute the action yourself — just output the ACTION: line. "
        "The system will ask the user to confirm before executing.\n\n"
        "EXAMPLES:\n"
        'User: "Move the IGCSE Physics lesson on July 10 to 16:00"\n'
        "Assistant: I can reschedule lesson L-2026-010 (IGCSE Physics) from July 10 14:00 to July 10 16:00. Shall I proceed?\n"
        'ACTION:{"operation":"reschedule","params":{"lesson_id":"L-2026-010","start_time":"16:00"}}\n\n'
        'User: "Move the Python lesson on July 16 to 14:00-16:00"\n'
        "Assistant: I can reschedule lesson L-2026-020 (Python) start to 14:00 and end to 16:00. Shall I proceed?\n"
        'ACTION:{"operation":"reschedule","params":{"lesson_id":"L-2026-020","start_time":"14:00","end_time":"16:00"}}\n\n'
        'User: "ICT Python course on 24/2 and 17/3, 3:10-4:10"\n'
        "Assistant: I see ICT Python course dates on 24/2 and 17/3 at 3:10-4:10. "
        "Which school is this for, and would you like me to create new lessons or reschedule?\n"
        '(No ACTION block — intent is unclear, ask first.)\n\n'
        'User: "Create new lessons for ICT Python at St. Mary\'s"\n'
        'Assistant: I will create 2 ICT Python lessons at St. Mary\'s. Shall I proceed?\n'
        'ACTION:{"operation":"create","params":{"course_name":"ICT Python AI Advanced Course","school_name":"St. Mary\'s School","date":"2026-02-24","start_time":"15:10","end_time":"16:10"}}\n'
        'ACTION:{"operation":"create","params":{"course_name":"ICT Python AI Advanced Course","school_name":"St. Mary\'s School","date":"2026-03-17","start_time":"15:10","end_time":"16:10"}}\n\n'
        'User: "Create a lesson for Advanced Rocketry at St. Mary\'s on 24/2 3:10-4:10"\n'
        'Assistant: The course "Advanced Rocketry" doesn\'t exist in our system. Would you like me to create it first?\n'
        '(No ACTION block — course not found, ask to create it first.)\n\n'
        'User: "Create a lesson for ICT Python at St. Mary\'s School on 24/2"\n'
        'Assistant: The school "St. Mary\'s School" doesn\'t exist in our system. Would you like me to create it first?\n'
        '(No ACTION block — school not found, ask to create it first.)\n\n'
        f"TODAY is {day_name} {today} (YYYY-MM-DD). "
        "Use this as your reference for 'today', 'tomorrow', 'yesterday', "
        "'next week', 'this week', 'next Monday', etc. "
        "When the user asks about a relative date, compute the exact date from this reference.\n"
        f"COUNTS: {counts}\n"
        f"COURSE CATALOG (course_id : course_name):\n"
        f"{chr(10).join(f'  {c}' for c in course_catalog)}\n"
        f"SCHOOL CATALOG (school_id : school_name):\n"
        f"{chr(10).join(f'  {s}' for s in school_catalog)}\n"
        f"UNASSIGNED lessons total={len(unassigned_all)}, soonest: {[_fmt(r) for r in unassigned_all[:12]]}\n"
        f"URGENT (within a week) total={len(urgent_all)}: "
        f"{[{'code': r.get('lesson_code'), 'date': str(r.get('lesson_date') or ''), 'reason': r.get('reason')} for r in urgent_all[:12]]}\n"
        f"UPCOMING lessons: {upcoming}\n"
    )
    # Inject pre-resolved school/course from frontend dropdown selection
    # If no frontend IDs, try server-side fuzzy match from message text
    if not resolved_school_id or not resolved_course_id:
        auto_sid, auto_cid = _fuzzy_resolve_names(message, db)
        if not resolved_school_id:
            resolved_school_id = auto_sid
        if not resolved_course_id:
            resolved_course_id = auto_cid
    resolved_hint = ""
    if resolved_school_id:
        sr = db.table("schools").select("school_id,school_name").eq("school_id", resolved_school_id).limit(1).execute().data
        if sr:
            resolved_hint += f"PRE-RESOLVED SCHOOL: school_id={sr[0]['school_id']}, school_name={sr[0]['school_name']}\n"
    if resolved_course_id:
        cr = db.table("courses").select("course_id,course_name").eq("course_id", resolved_course_id).limit(1).execute().data
        if cr:
            resolved_hint += f"PRE-RESOLVED COURSE: course_id={cr[0]['course_id']}, course_name={cr[0]['course_name']}\n"
    if resolved_hint:
        system += "\n" + resolved_hint
        system += "When PRE-RESOLVED SCHOOL/COURSE is shown, use BOTH the school_name/course_name AND school_id/course_id in ACTION params. Do NOT verify the name against the catalog — it is already confirmed to exist.\n"
    full_messages = [{"role": "system", "content": system}]
    full_messages += [{"role": h.get("role", "user"), "content": h.get("content", "")} for h in history[-4:]]
    full_messages.append({"role": "user", "content": message})

    result = _llm_chat(full_messages)
    if result is not None:
        return {"reply": result["content"] or "(empty response)", "source": settings.LLM_PROVIDER}
    return {
        "reply": (
            "I can't reach the language model right now, but I can still answer "
            "operational questions like 'show unassigned lessons', 'urgent within a week', "
            "'today's schedule', or 'database summary'. To add data, use the input forms."
        ),
        "source": "fallback",
    }


def _get_cache_key(message: str, history: list[dict] | None = None) -> str:
    """Generate cache key from message and recent history."""
    history_str = str(history[-2:]) if history else ""
    return hashlib.md5((message + history_str).encode()).hexdigest()

def _get_cached_response(cache_key: str) -> dict | None:
    """Check cache for existing response."""
    return _RESPONSE_CACHE.get(cache_key)

def _set_cached_response(cache_key: str, response: dict):
    """Cache a response with LRU eviction."""
    if len(_RESPONSE_CACHE) >= _CACHE_MAX_SIZE:
        # Remove oldest entry (simple FIFO)
        _RESPONSE_CACHE.pop(next(iter(_RESPONSE_CACHE)))
    _RESPONSE_CACHE[cache_key] = response

def answer(db: Client, message: str, history: list[dict] | None = None,
           *, resolved_school_id: str | None = None,
           resolved_course_id: str | None = None) -> dict:
    lang = has_chinese(message)
    eng_msg = message
    eng_history = history or []
    
    # Check cache first for repeated queries
    cache_key = _get_cache_key(eng_msg, eng_history)
    cached = _get_cached_response(cache_key)
    if cached:
        if lang and cached.get("reply"):
            cached["reply"] = from_english(cached["reply"], lang)
        cached["cached"] = True
        return cached
    
    # Try rule-based responses FIRST for instant results (common queries)
    rule_result = _deterministic_answer(db, eng_msg)
    if rule_result:
        if lang and rule_result.get("reply"):
            rule_result["reply"] = from_english(rule_result["reply"], lang)
        rule_result["cached"] = False
        _set_cached_response(cache_key, rule_result)
        return rule_result
    
    # Fall back to LLM for complex queries
    res = _llm_reply(db, eng_msg, eng_history or [], lang=lang,
                     resolved_school_id=resolved_school_id,
                     resolved_course_id=resolved_course_id)
    if res["source"] != "fallback":
        reply = res.get("reply", "")
        match = re.search(r'^ACTION:\s*(\{.*\})\s*$', reply, re.MULTILINE)
        if match:
            try:
                action_data = json.loads(match.group(1))
                clean_reply = re.sub(r'^ACTION:\s*\{.*\}\s*', '', reply, flags=re.MULTILINE).strip()
                res["reply"] = clean_reply
                res["pendingAction"] = action_data
            except (json.JSONDecodeError, ValueError):
                pass
        if lang:
            res["reply"] = from_english(res.get("reply", ""), lang)
        res["cached"] = False
        _set_cached_response(cache_key, res)
        return res
    
    # Final fallback to deterministic answers if LLM fails
    det = _deterministic_answer(db, eng_msg) or res
    if lang and det.get("reply"):
        det["reply"] = from_english(det["reply"], lang)
    det["cached"] = False
    _set_cached_response(cache_key, det)
    return det


# --- Execute pending actions (after user confirmation) -----------------------

def execute_operation(db: Client, operation: str, params: dict) -> dict:
    """Execute a user-confirmed data-modifying operation."""
    if operation == "reschedule":
        lesson_code = params.get("lesson_id")
        if not lesson_code:
            return {"ok": False, "error": "Missing lesson_id"}
        # Resolve lesson_code to uuid if needed
        lessons = db.table("lessons").select("id").eq("lesson_id", lesson_code).limit(1).execute().data
        if not lessons:
            return {"ok": False, "error": f"Lesson {lesson_code} not found"}
        lesson_id = lessons[0]["id"]
        updates = {}
        if params.get("date"): updates["date"] = params["date"]
        if params.get("start_time"): updates["start_time"] = params["start_time"]
        if params.get("end_time"): updates["end_time"] = params["end_time"]
        if not updates:
            return {"ok": False, "error": "No fields to update"}
        repos.update_row(db, "lessons", lesson_id, updates)
        return {"ok": True, "message": f"Lesson {lesson_code} updated."}

    if operation == "create":
        course_id = params.get("course_id")
        course_name = params.get("course_name")
        if not course_id and course_name:
            rows = db.table("courses").select("course_id").ilike("course_name", course_name).limit(1).execute().data
            if rows:
                course_id = rows[0]["course_id"]
            # Exact-match fallback
            if not course_id:
                rows = db.table("courses").select("course_id").eq("course_name", course_name).limit(1).execute().data
                if rows:
                    course_id = rows[0]["course_id"]
        school_name = params.get("school_name")
        school_id = params.get("school_id")
        if not school_id and school_name:
            school_rows = db.table("schools").select("school_id").ilike("school_name", school_name).limit(1).execute().data
            if school_rows:
                school_id = school_rows[0]["school_id"]
            # Exact-match fallback
            if not school_id:
                school_rows = db.table("schools").select("school_id").eq("school_name", school_name).limit(1).execute().data
                if school_rows:
                    school_id = school_rows[0]["school_id"]
        date_val = params.get("date")
        if not course_id or not date_val:
            return {"ok": False, "error": "Missing course or date"}
        if not school_name:
            return {"ok": False, "error": "Missing school — please specify which school this lesson is for"}
        if not school_id:
            return {"ok": False, "error": f"School '{school_name}' not found — please create it first"}
        lesson_code = codes.next_lesson_code(db, date=date_val, start_time=params.get("start_time"), course_name=params.get("course_name"))
        payload = {
            "date": date_val,
            "lesson_id": lesson_code,
            "course_id": course_id,
            "status": "Unassigned",
            "max_tutors": params.get("max_tutors", 1),
        }
        if params.get("start_time"): payload["start_time"] = params["start_time"]
        if params.get("end_time"): payload["end_time"] = params["end_time"]
        repos.insert_row(db, "lessons", payload)
        return {"ok": True, "message": f"Lesson {lesson_code} created."}

    if operation == "create_course":
        course_name = params.get("course_name")
        if not course_name:
            return {"ok": False, "error": "Missing course_name"}
        school_name = params.get("school_name")
        school_id = None
        if school_name:
            school_rows = db.table("schools").select("school_id").ilike("school_name", school_name).limit(1).execute().data
            if school_rows:
                school_id = school_rows[0]["school_id"]
        course_id = codes.next_course_id(db, course_name)
        payload = {"course_id": course_id, "course_name": course_name}
        if school_id:
            payload["school_id"] = school_id
        for opt in ("course_topic", "course_types", "revenue_per_lesson"):
            if params.get(opt):
                payload[opt] = params[opt]
        repos.insert_row(db, "courses", payload)
        return {"ok": True, "message": f"Course {course_id} ({course_name}) created. You can now create lessons for this course."}

    if operation == "create_school":
        school_name = params.get("school_name")
        if not school_name:
            return {"ok": False, "error": "Missing school_name"}
        school_id = codes.next_school_id(db)
        payload = {"school_id": school_id, "school_name": school_name}
        repos.insert_row(db, "schools", payload)
        return {"ok": True, "message": f"School {school_id} ({school_name}) created."}

    if operation == "update":
        lesson_code = params.get("lesson_id")
        if not lesson_code:
            return {"ok": False, "error": "Missing lesson_id"}
        lessons = db.table("lessons").select("id").eq("lesson_id", lesson_code).limit(1).execute().data
        if not lessons:
            return {"ok": False, "error": f"Lesson {lesson_code} not found"}
        resolved = dict(params)
        course_name = resolved.pop("course", None) or resolved.pop("course_name", None)
        if course_name:
            rows = db.table("courses").select("course_id").ilike("course_name", course_name).limit(1).execute().data
            if rows:
                resolved["course_id"] = rows[0]["course_id"]
        updatable_fields = {"date", "start_time", "end_time", "status", "notes",
                           "lesson_material_link", "role", "max_tutors", "course_id",
                           "school_name"}
        updates = {k: v for k, v in resolved.items() if k in updatable_fields and k != "lesson_id"}
        if not updates:
            return {"ok": False, "error": "No valid fields to update"}
        try:
            repos.update_row(db, "lessons", lessons[0]["id"], updates)
        except Exception as e:
            err = str(e)
            if "column" in err and "does not exist" in err:
                col = err.split('"')[1] if '"' in err else err.split()[-1]
                db.table("lessons").execute_raw(f"alter table public.lessons add column if not exists {col} text;")
                repos.update_row(db, "lessons", lessons[0]["id"], updates)
            else:
                raise
        return {"ok": True, "message": f"Lesson {lesson_code} updated."}

    if operation == "delete":
        lesson_code = params.get("lesson_id")
        if not lesson_code:
            return {"ok": False, "error": "Missing lesson_id"}
        lessons = db.table("lessons").select("id").eq("lesson_id", lesson_code).limit(1).execute().data
        if not lessons:
            return {"ok": False, "error": f"Lesson {lesson_code} not found"}
        repos.delete_row(db, "lessons", lessons[0]["id"])
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
