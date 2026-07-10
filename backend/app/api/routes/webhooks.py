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

import logging
import secrets
import sys
from collections import Counter
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from postgrest import SyncPostgrestClient

from app.core.config import settings
from app.core.database import get_supabase
from app.services import repos, scheduling

logger = logging.getLogger("vinci.webhook")
router = APIRouter()


def _extract_text(payload: dict) -> str:
    def _val(v):
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            return str(v.get("body") or v.get("text") or v.get("title") or "")
        return str(v) if v else ""
        
    # Handle WATI/WhatsApp Cloud API 'interactive' payload structure
    interactive = payload.get("interactive") or (payload.get("message") or {}).get("interactive") or {}
    if isinstance(interactive, dict):
        # Check button reply
        btn_reply = interactive.get("button_reply") or {}
        if isinstance(btn_reply, dict):
            val = _val(btn_reply.get("title") or btn_reply.get("id"))
            if val:
                return val
        # Check list reply
        list_reply = interactive.get("list_reply") or {}
        if isinstance(list_reply, dict):
            val = _val(list_reply.get("title") or list_reply.get("id"))
            if val:
                return val

    # Legacy flat button structures
    for btn_key in ("buttonReply", "interactiveButtonReply"):
        btn = payload.get(btn_key) or {}
        for field in ("text", "title", "id"):
            if isinstance(btn, dict):
                val = _val(btn.get(field))
                if val:
                    return val

    # Fallback to text fields
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
            if kw.isascii():
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, low):
                    scores[intent] += 1
            else:
                if kw in low:
                    scores[intent] += 1
    if not scores:
        return None
    intent_order = ["accept", "cancel", "reschedule"]
    max_score = max(scores.values())
    for intent in intent_order:
        if scores.get(intent, 0) == max_score:
            return intent
    return scores.most_common(1)[0][0]


def _soonest(views: list[dict]) -> dict | None:
    if not views:
        return None
    today = date.today().isoformat()
    upcoming = [v for v in views if str(v.get("lesson_date")) >= today]
    pool = upcoming or views
    return sorted(pool, key=lambda v: (str(v.get("lesson_date")), str(v.get("start_time") or "")))[0]


@router.post("/webhooks/wati")
async def wati_webhook(
    request: Request,
    secret: str = "",
    authorization: str = Header(default=""),
    db: SyncPostgrestClient = Depends(get_supabase),
):
    _req_id = secrets.token_hex(4)

    try:
        # 1. Auth check — accept via query param (?secret=...) since WATI
        #    doesn't support custom headers, or via Authorization header.
        if settings.WATI_WEBHOOK_SECRET:
            expected_bearer = f"Bearer {settings.WATI_WEBHOOK_SECRET}"
            header_ok = secrets.compare_digest(authorization.strip(), expected_bearer)
            param_ok = secrets.compare_digest(secret.strip(), settings.WATI_WEBHOOK_SECRET)
            if not header_ok and not param_ok:
                logger.warning("[%s] bad webhook token (header=%s..., param=%s...)",
                               _req_id, authorization[:30], secret[:10])
                raise HTTPException(status_code=403, detail="bad token")

        # 2. Parse payload
        try:
            payload = await request.json()
        except Exception:
            form = await request.form()
            payload = dict(form)

        logger.info("[%s] webhook received  eventType=%s  owner=%s  keys=%s",
                     _req_id,
                     payload.get("eventType", "N/A"),
                     payload.get("owner", "N/A"),
                     list(payload.keys()))

        # 3. Trigger guard
        event_type = str(payload.get("eventType", "")).lower()
        if event_type and event_type not in ("message", "interactive"):
            logger.info("[%s] ignored — eventType=%s", _req_id, event_type)
            return {"status": "ignored", "reason": f"event '{event_type}'"}
        if payload.get("owner") in (True, "true"):
            logger.info("[%s] ignored — owner=true", _req_id)
            return {"status": "ignored", "reason": "outgoing message"}

        # 4. Extract + classify text
        text = _extract_text(payload)
        intent = _classify(text)
        logger.info("[%s] extract='%s'  intent=%s", _req_id, text[:80], intent)

        if not intent:
            return {"status": "ignored", "reason": "no accept/cancel/reschedule keyword", "text": text}

        # 5. Phone matching
        raw_phone = payload.get("waId") or payload.get("whatsappNumber") or payload.get("phone") or ""
        candidates = repos.teachers_by_phone(db, raw_phone)
        logger.info("[%s] phone=%s  candidates=%s",
                     _req_id, raw_phone,
                     [c.get("teacher_id") for c in candidates])

        if not candidates:
            return {"status": "no_match", "reason": "phone not found", "phone": str(raw_phone)}

        # 6. Route by intent
        if intent == "accept":
            chosen, lesson = None, None
            for cand in candidates:
                tid = cand["teacher_id"]
                pending = repos.offers_for_teacher(db, tid, status="pending")
                logger.info("[%s] cand=%s  pending_offers=%s",
                             _req_id, tid, [o.get("lesson_id") for o in pending])
                # Pick the most recently blasted offer, not the soonest lesson.
                # This way, tapping "Accept" on a new lesson's message accepts
                # that lesson — not an older lesson that happens to be sooner.
                pending.sort(key=lambda o: str(o.get("last_blast_at") or ""), reverse=True)
                for offer in pending:
                    v = repos.get_lesson_view(db, offer["lesson_id"])
                    if v:
                        chosen, lesson = cand, v
                        break
                if chosen:
                    break
            if not lesson:
                logger.warning("[%s] no pending offer for any candidate", _req_id)
                return {"status": "no_match", "reason": "no pending offer for this number"}
            logger.info("[%s] accepting — teacher=%s  lesson=%s", _req_id, chosen["teacher_id"], lesson.get("id"))
            result = scheduling.record_acceptance(db, lesson["id"], chosen["teacher_id"])
            logger.info("[%s] accept result=%s", _req_id, result)
            return {"status": "ok", "intent": intent, "tutor": chosen["teacher_name"], **result}

        teacher = candidates[0]
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

    except HTTPException:
        raise
    except Exception:
        logger.exception("[%s] unhandled webhook error", _req_id)
        raise HTTPException(status_code=500, detail="internal error")
