"""Inbound WATI webhook — ports `reply handling.js` + `cancellation handling.js`.

Point your WATI webhook at:
    POST  https://<backend>/api/webhooks/wati
With header:  Authorization: Bearer <WATI_WEBHOOK_SECRET>

A typed tutor reply is classified into one intent:
  * "accept"     -> mark their soonest pending offer accepted
  * "cancel"     -> unassign their lesson, alert admin, re-blast the pool
  * "reschedule" -> same as cancel but flagged as a reschedule

Button/interactive taps and outgoing (owner=true) messages are ignored, matching
the original guard logic.
"""

from __future__ import annotations

import secrets
from collections import Counter
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from postgrest import SyncPostgrestClient

from app.core.config import settings
from app.core.database import get_supabase
from app.services import repos, scheduling

router = APIRouter()


def _extract_text(payload: dict) -> str:
    def _val(v):
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            return str(v.get("body") or v.get("text") or v.get("title") or "")
        return str(v) if v else ""
    # Try every known WATI webhook field for the user's reply text
    for btn_key in ("buttonReply", "interactiveButtonReply"):
        btn = payload.get(btn_key) or {}
        for field in ("text", "title", "id"):
            val = _val(btn.get(field))
            if val:
                return val
    return (
        _val(payload.get("text"))
        or _val((payload.get("listReply") or {}).get("title"))
        or _val((payload.get("message") or {}).get("text"))
        or _val((payload.get("message") or {}).get("body"))
        or (payload.get("msg") or {}).get("body", "")
        or _val(payload.get("body"))
        or ""
    ).strip()


INTENT_KEYWORDS = {
    "accept": ["accept", "yes", "i'll take it", "i will take", "i'll do it", "接受", "可以"],
    "cancel": ["cancel", "can't make", "cannot make", "unavailable", "can't attend", "取消", "不能"],
    "reschedule": ["reschedule", "change date", "move", "different time", "another day", "改期", "改時間"],
}


def _classify(text: str) -> str | None:
    import re
    low = text.lower().strip()
    scores = Counter()
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            # Use \b word boundaries only for ASCII keywords; non-ASCII
            # (Chinese characters) don't match \b in Python's re, so fall
            # back to a simple substring check for those.
            if kw.isascii():
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, low):
                    scores[intent] += 1
            else:
                if kw in low:
                    scores[intent] += 1
    if not scores:
        return None
    # Deterministic tie-breaking: use stable sort order (accept, cancel, reschedule)
    intent_order = ["accept", "cancel", "reschedule"]
    max_score = max(scores.values())
    for intent in intent_order:
        if scores.get(intent, 0) == max_score:
            return intent
    return scores.most_common(1)[0][0]


def _soonest(views: list[dict]) -> dict | None:
    """Pick the soonest upcoming lesson (fallback to soonest overall)."""
    if not views:
        return None
    today = date.today().isoformat()
    upcoming = [v for v in views if str(v.get("lesson_date")) >= today]
    pool = upcoming or views
    return sorted(pool, key=lambda v: (str(v.get("lesson_date")), str(v.get("start_time") or "")))[0]


@router.post("/webhooks/wati")
async def wati_webhook(
    request: Request,
    authorization: str = Header(default=""),
    db: SyncPostgrestClient = Depends(get_supabase),
):
    # 1. Reject spoofed calls — expect "Bearer <secret>" in Authorization header
    if settings.WATI_WEBHOOK_SECRET:
        expected = f"Bearer {settings.WATI_WEBHOOK_SECRET}"
        if not secrets.compare_digest(authorization.strip(), expected):
            raise HTTPException(status_code=403, detail="bad token")

    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001 - WATI sometimes posts form-encoded
        form = await request.form()
        payload = dict(form)

    # 2. Trigger guard: only act on an incoming, non-owner text-ish or
    #    interactive (button reply) message
    event_type = str(payload.get("eventType", "")).lower()
    if event_type and event_type not in ("message", "interactive"):
        return {"status": "ignored", "reason": f"event '{event_type}'"}
    if payload.get("owner") in (True, "true"):
        return {"status": "ignored", "reason": "outgoing message"}

    text = _extract_text(payload)
    intent = _classify(text)
    if not intent:
        return {"status": "ignored", "reason": "no accept/cancel/reschedule keyword", "text": text}

    raw_phone = payload.get("waId") or payload.get("whatsappNumber") or payload.get("phone") or ""
    candidates = repos.teachers_by_phone(db, raw_phone)
    if not candidates:
        return {"status": "no_match", "reason": "phone not found", "phone": str(raw_phone)}

    # 3. Route by intent
    if intent == "accept":
        # Among teachers sharing this number, accept for the one who actually
        # has a pending offer (the soonest such lesson).
        chosen, lesson = None, None
        for cand in candidates:
            pending = repos.offers_for_teacher(db, cand["teacher_id"], status="pending")
            views = [repos.get_lesson_view(db, o["lesson_id"]) for o in pending]
            v = _soonest([x for x in views if x])
            if v:
                chosen, lesson = cand, v
                break
        if not lesson:
            return {"status": "no_match", "reason": "no pending offer for this number"}
        result = scheduling.record_acceptance(db, lesson["id"], chosen["teacher_id"])
        return {"status": "ok", "intent": intent, "tutor": chosen["teacher_name"], **result}

    teacher = candidates[0]

    # cancel / reschedule — find the tutor's lesson (assigned first, else accepted offer)
    assigned = repos.assigned_lessons_for_teacher(db, teacher["teacher_id"])
    lesson = _soonest(assigned)
    if not lesson:
        accepted = repos.offers_for_teacher(db, teacher["teacher_id"], status="accepted")
        views = [repos.get_lesson_view(db, o["lesson_id"]) for o in accepted]
        lesson = _soonest([v for v in views if v])
    if not lesson:
        return {"status": "no_match", "reason": "no assigned/accepted lesson for tutor"}

    result = scheduling.handle_cancellation(db, lesson["id"], teacher["teacher_id"], intent)
    return {"status": "ok", "intent": intent, "tutor": teacher["teacher_name"], **result}
