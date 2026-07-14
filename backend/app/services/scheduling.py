"""Automated triggers — the heart of Phase 1, ported from the four Apps Scripts.

Maps the design's Phase-1 bullet points to functions:
  * Class scheduling / tutor reminders  -> blast_lesson() + run_due_reminders()
  * Receiving tutor acceptances         -> record_acceptance()  (called by webhook)
  * Choosing tutors from the pool       -> assign_tutor()
  * Sending out necessary files         -> assign_tutor(send_files=True) (material link)
  * Cancellation / reschedule           -> handle_cancellation()  (called by webhook)

All WhatsApp traffic goes through app.services.wati; all DB access through
app.services.repos; everything is logged to lesson_events for traceability.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from postgrest import SyncPostgrestClient

Client = SyncPostgrestClient

from app.core.config import settings
from app.services import codes, repos, urgency, wati


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_ts(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _phone_for(teacher: dict, toggle: list[int]) -> str:
    """Real WhatsApp number, or alternate between the two fallback test numbers
    (same rule the calendar script used when a tutor had no number)."""
    phone = wati.normalize_phone(teacher.get("whatsapp_number"))
    if phone:
        return phone
    if toggle[0] % 2 == 0:
        phone = settings.FALLBACK_WHATSAPP_HK
    else:
        phone = settings.FALLBACK_WHATSAPP_ID
    toggle[0] += 1
    return phone


# --- 1. Blast a lesson to the tutor pool -----------------------------------

def blast_lesson(
    db: Client,
    lesson_id: str,
    *,
    force_all: bool = False,
    exclude_teacher_id: str | None = None,
) -> dict:
    """Send `unassigned_lesson_notification` to the lesson's tutor pool.

    If the lesson has no pool yet (or ``force_all``), seed the pool from all
    active teachers — this is the "first blast" / re-blast-everyone path.
    """
    lesson = repos.get_lesson_view(db, lesson_id)
    if not lesson:
        raise ValueError(f"lesson {lesson_id} not found")

    ctx = repos.lesson_wati_context(lesson)
    offers = repos.get_offers(db, lesson_id)

    if offers and not force_all:
        teachers = [repos.get_row(db, "teachers", o["teacher_id"]) for o in offers if o["offer_status"] == "pending"]
    else:
        teachers = db.table("teachers").select("*").eq("status", "Active").execute().data or []

    sent, failed = 0, 0
    toggle = [0]
    for teacher in filter(None, teachers):
        if exclude_teacher_id and teacher["teacher_id"] == exclude_teacher_id:
            continue
        phone = _phone_for(teacher, toggle)
        res = wati.send_unassigned_notification(phone, ctx)
        repos.upsert_offer(
            db, lesson_id, teacher["teacher_id"],
            offer_status="pending",
            last_blast_at=_iso_now(),
            last_send_result="Sent" if res["ok"] else f"Failed: {res['error']}",
        )
        repos.log_event(db, lesson_id, teacher["teacher_id"], "blast", {"ok": res["ok"], "phone": phone})
        sent += res["ok"]
        failed += (not res["ok"])

    return {"lesson_id": lesson_id, "lesson_code": ctx["lesson_code"], "sent": sent, "failed": failed}


# --- 2. The 24h reminder / re-blast sweep (scheduled) ----------------------

def run_due_reminders(db: Client) -> dict:
    """For every unassigned lesson, (re)blast pending tutors whose last blast
    is older than REBLAST_INTERVAL_HOURS. Seeds a pool for brand-new lessons.
    This is what the Render Cron Job calls hourly."""
    interval = settings.REBLAST_INTERVAL_HOURS * 3600
    now = datetime.now(timezone.utc)
    reblasted = skipped = seeded = 0
    touched: list[str] = []

    for lesson in repos.list_unassigned(db):
        lesson_id = lesson["id"]
        ctx = repos.lesson_wati_context(lesson)
        offers = repos.get_offers(db, lesson_id)

        if not offers:
            res = blast_lesson(db, lesson_id, force_all=True)
            seeded += res["sent"]
            touched.append(ctx["lesson_code"])
            continue

        for offer in offers:
            if offer["offer_status"] != "pending":
                skipped += 1
                continue
            last = _parse_ts(offer.get("last_blast_at"))
            if last and (now - last).total_seconds() < interval:
                skipped += 1
                continue
            teacher = repos.get_row(db, "teachers", offer["teacher_id"])
            if not teacher:
                continue
            phone = wati.normalize_phone(teacher.get("whatsapp_number")) or settings.FALLBACK_WHATSAPP_HK
            res = wati.send_unassigned_notification(phone, ctx)
            repos.upsert_offer(
                db, lesson_id, teacher["teacher_id"],
                offer_status="pending",
                last_blast_at=_iso_now(),
                last_send_result="Re-sent" if res["ok"] else f"Failed: {res['error']}",
            )
            repos.log_event(db, lesson_id, teacher["teacher_id"], "reblast", {"ok": res["ok"]})
            reblasted += 1
        touched.append(ctx["lesson_code"])

    return {"reblasted": reblasted, "seeded": seeded, "skipped": skipped, "lessons": touched}


# --- 3. Receive a tutor acceptance (called by the WATI webhook) ------------

def record_acceptance(db: Client, lesson_id: str, teacher_id: str) -> dict:
    repos.set_offer_status(db, lesson_id, teacher_id, "accepted", responded_at=_iso_now())
    repos.log_event(db, lesson_id, teacher_id, "accept", {})
    # Bump the lesson's raw status so the Dashboard shows it as "Has Acceptance"
    # instead of "Unassigned" — this makes the Assign button visible.
    lesson = repos.get_lesson_view(db, lesson_id)
    if lesson:
        raw = (lesson.get("raw_status") or "").lower()
        if raw in ("unassigned", "offersent", ""):
            repos.update_row(db, "lessons", lesson_id, {"status": "HasAcceptance"})

    # WhatsApp confirmation to the tutor so they know the acceptance went through
    teacher = repos.get_row(db, "teachers", teacher_id)
    if teacher:
        phone = wati.normalize_phone(teacher.get("whatsapp_number"))
        if phone and lesson:
            ctx = repos.lesson_wati_context(lesson)
            ctx["tutor_name"] = teacher.get("teacher_name", "")
            ctx["lesson_material_link"] = ""  # no material yet — admin hasn't assigned
            res = wati.send_confirmation(phone, ctx)
            repos.log_event(db, lesson_id, teacher_id, "acceptance_confirmed", {"ok": res["ok"]})

    return {"lesson_id": lesson_id, "teacher_id": teacher_id, "offer_status": "accepted"}


# --- 4. Choose a tutor from the pool + 5. send the material link -----------

def assign_tutor(
    db: Client,
    lesson_id: str,
    teacher_id: str,
    *,
    send_files: bool = True,
    force_reassign: bool = False,
) -> dict:
    """Assign an (accepted) tutor to a lesson and send the confirmation message
    carrying the lesson-material link.

    Uses an atomic DB stored procedure (assign_tutor_atomic) with SELECT FOR UPDATE
    to prevent race conditions when multiple admins assign simultaneously.

    Raises:
        ValueError: 'DUPLICATE' prefix — same tutor already assigned.
        ValueError: 'CLASH' prefix — different tutor already assigned and force_reassign=False.
        ValueError: 'FULL' prefix — lesson is at max tutor capacity.
    """
    teacher = repos.get_row(db, "teachers", teacher_id)
    if not teacher:
        raise ValueError(f"teacher {teacher_id} not found")
    lesson = repos.get_lesson_view(db, lesson_id)
    if not lesson:
        raise ValueError(f"lesson {lesson_id} not found")

    max_t = max(1, int(lesson.get("max_tutors") or 1))
    assigned_count = lesson.get("assigned_count", 0)

    # Clash check: when max_tutors is 1, replacing the existing tutor requires confirmation.
    # For multi-tutor lessons we allow additional tutors until capacity is reached.
    existing_teacher_id = lesson.get("assigned_teacher_id")
    if max_t == 1 and existing_teacher_id and existing_teacher_id != teacher_id and not force_reassign:
        existing_name = lesson.get("assigned_teacher_name", existing_teacher_id)
        raise ValueError(f"CLASH: This lesson already has an assigned tutor ({existing_name}). Confirm re-assignment to proceed.")

    # Atomic assignment via stored procedure (SELECT FOR UPDATE + capacity check)
    try:
        result = db.rpc("assign_tutor_atomic", {
            "p_lesson_id": lesson_id,
            "p_teacher_id": teacher_id,
            "p_max_tutors": max_t,
        }).execute()
        raw = result.data if hasattr(result, 'data') else result
    except Exception as exc:
        raise ValueError(f"DB error during atomic assignment: {exc}")

    if isinstance(raw, (dict, list)):
        data = raw[0] if isinstance(raw, list) else raw
    else:
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            raise ValueError(f"Unexpected RPC response: {raw}")

    if not data.get("success", False):
        raise ValueError(data.get("message", "Assignment failed"))

    repos.log_event(db, lesson_id, teacher_id, "assign", {"force_reassign": force_reassign, "method": "atomic_rpc"})

    result: dict | None = None
    if send_files:
        ctx = repos.lesson_wati_context(lesson)
        ctx["tutor_name"] = teacher.get("teacher_name", "")
        phone = wati.normalize_phone(teacher.get("whatsapp_number")) or settings.FALLBACK_WHATSAPP_HK
        result = wati.send_confirmation(phone, ctx)
        event = "material_sent" if ctx.get("lesson_material_link") else "confirmation_sent"
        repos.log_event(db, lesson_id, teacher_id, event, {"ok": result["ok"]})

    assigned_count = data.get("assigned_count", 1)
    
    return {
        "lesson_id": lesson_id,
        "assigned_teacher_id": teacher_id,
        "status": "assigned" if assigned_count >= max_t else "hasacceptance",
        "assigned_count": assigned_count,
        "max_tutors": max_t,
        "confirmation": result,
    }


# --- 6. Cancellation / reschedule (called by the WATI webhook) -------------

def handle_cancellation(db: Client, lesson_id: str, teacher_id: str | None, intent: str) -> dict:
    """Unassign the lesson, alert the admin, and re-blast the remaining pool."""
    lesson = repos.get_lesson_view(db, lesson_id)
    if not lesson:
        raise ValueError(f"lesson {lesson_id} not found")

    unassigned_label = (
        "Tutor unassigned & class is within a week of today"
        if lesson.get("within_a_week")
        else "Tutor unassigned & class is beyond a week from today"
    )
    repos.update_row(db, "lessons", lesson_id, {
        "teacher_id": None,
        "tutor_assignment": unassigned_label,
        "status": "OfferSent",  # reblast will go out; keep visible in dashboard
    })
    if teacher_id:
        repos.set_offer_status(db, lesson_id, teacher_id, "withdrawn", responded_at=_iso_now())
    repos.log_event(db, lesson_id, teacher_id, "reschedule" if intent == "reschedule" else "cancel", {})

    # Notify admin
    admin_res = None
    if settings.ADMIN_WHATSAPP:
        ctx = repos.lesson_wati_context(lesson)
        teacher = repos.get_row(db, "teachers", teacher_id) if teacher_id else None
        ctx["tutor_name"] = (teacher or {}).get("teacher_name", "Unknown tutor")
        ctx["intent"] = intent
        admin_res = wati.send_admin_cancellation(settings.ADMIN_WHATSAPP, ctx)
        repos.log_event(db, lesson_id, None, "admin_notified", {"ok": admin_res["ok"]})

    # Re-blast everyone except the cancelling tutor
    reblast = blast_lesson(db, lesson_id, force_all=True, exclude_teacher_id=teacher_id)

    return {
        "lesson_id": lesson_id,
        "intent": intent,
        "admin_notified": bool(admin_res and admin_res["ok"]),
        "reblast": reblast,
    }


# --- Announce a new lesson + LLM-selected tutor outreach -------------------

def announce_lesson(db: Client, *, lesson_code, date, start_time, end_time, course, school, max_tutors=1, lesson_income=None, school_id=None, course_id=None) -> dict:
    """Create a lesson, ask the LLM which tutors fit, and WhatsApp them.

    `course` is matched to an existing course (so the lesson links via FK); the
    typed `school` is used as context for matching and the message.
    """
    from app.services import chatbot

    course_name, topic = (course or ""), ""
    if not course_id and course:
        rows = db.table("courses").select("*").ilike("course_name", f"%{course}%").limit(1).execute().data or []
        if not rows:
            rows = db.table("courses").select("*").eq("course_id", course).limit(1).execute().data or []
        if rows:
            course_id = rows[0]["course_id"]
            course_name = rows[0].get("course_name") or course
            topic = rows[0].get("course_topic") or ""
    elif course_id:
        row = repos.get_row(db, "courses", course_id)
        if row:
            course_name = row.get("course_name") or course or ""
            topic = row.get("course_topic") or ""

    date_str = str(date)
    if not lesson_code:
        lesson_code = codes.next_lesson_code(db, date=date_str, start_time=start_time, course_name=course_name)
    within = urgency.within_a_week(date_str)
    payload = {
        "date": date_str,
        "lesson_id": lesson_code,
        "status": "Unassigned",
        "max_tutors": max(1, int(max_tutors or 1)),
        "tutor_assignment": (
            "Tutor unassigned & class is within a week of today" if within
            else "Tutor unassigned & class is beyond a week from today"
        ),
    }
    
    if start_time:
        payload["start_time"] = start_time
    if end_time:
        payload["end_time"] = end_time
    if course_id:
        payload["course_id"] = course_id
    if school:
        payload["school_name"] = school
    if lesson_income is not None:
        payload["lesson_income"] = lesson_income
    if school_id:
        payload["school_id"] = school_id

    lesson = repos.insert_row(db, "lessons", payload)
    lesson_id = lesson["id"]

    ctx = {
        "lesson_code": lesson_code or "",
        "course_name": course_name,
        "school_name": school or "",
        "date": date_str,
        "start_time": (start_time or "")[:5],
        "end_time": (end_time or "")[:5],
        "urgency": urgency.urgency_label(date_str),
    }

    # Message a pool a bit larger than the cap so enough tutors can accept.
    pool_size = min(max(int(max_tutors or 1) * 2, 4), 12)
    teacher_ids, llm_used = chatbot.select_tutor_ids(db, course=course_name, school=school or "", topic=topic, limit=pool_size)

    messaged = []
    for tid in teacher_ids:
        teacher = repos.get_row(db, "teachers", tid)
        if not teacher:
            continue
        phone = wati.normalize_phone(teacher.get("whatsapp_number")) or settings.FALLBACK_WHATSAPP_HK
        res = wati.send_unassigned_notification(phone, ctx)
        repos.upsert_offer(
            db, lesson_id, tid,
            offer_status="pending",
            last_blast_at=_iso_now(),
            last_send_result="Sent" if res["ok"] else f"Failed: {res['error']}",
        )
        repos.log_event(db, lesson_id, tid, "blast", {"ok": res["ok"], "via": "announce", "llm": llm_used})
        messaged.append({"teacher_id": tid, "name": teacher.get("teacher_name"), "ok": res["ok"]})

    return {
        "lesson_id": lesson_id,
        "lesson_code": lesson_code,
        "course": course_name,
        "school": school,
        "max_tutors": payload["max_tutors"],
        "llm_used": llm_used,
        "count": len(messaged),
        "messaged": messaged,
    }
