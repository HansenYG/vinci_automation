"""WATI (WhatsApp) client — ported from the original Google Apps Scripts.

The scripts used two endpoints; we standardise on the bulk
``/api/v1/sendTemplateMessages`` form (receivers + customParams) because it
also works for a single receiver and covers all three templates:

  * unassigned_lesson_notification          (lesson needs a tutor)
  * tutor_confirmation_extra_info           (you're confirmed + material link)
  * tutor_cancellation_or_reschedule_admin_reminder (alert the admin)

Every send returns a uniform ``{ok, code, body, error}`` dict and never
raises, mirroring the defensive logging the Apps Scripts relied on.
"""

from __future__ import annotations

import re
from typing import Any

import httpx

from app.core.config import settings


def normalize_phone(raw: Any) -> str:
    """Digits only, no leading + — exactly what WATI's whatsappNumber wants."""
    return re.sub(r"\D", "", "" if raw is None else str(raw))


def _auth_header() -> str:
    # Tolerate a token pasted with or without a leading "Bearer ".
    token = (settings.WATI_ACCESS_TOKEN or "").strip()
    token = re.sub(r"^Bearer\s+", "", token, flags=re.IGNORECASE)
    return f"Bearer {token}"


def send_template_message(
    phone: str,
    template_name: str,
    params: dict[str, str],
    broadcast_name: str | None = None,
) -> dict[str, Any]:
    """Send one approved-template WhatsApp message via WATI.

    ``params`` maps the template's placeholder names to values. Returns
    ``{ok, code, body, error}`` and never raises.
    """
    if not settings.WATI_API_URL or not settings.WATI_ACCESS_TOKEN:
        return {"ok": False, "code": 0, "body": "", "error": "WATI not configured (set WATI_API_URL / WATI_ACCESS_TOKEN)"}

    clean_phone = normalize_phone(phone)
    if not clean_phone:
        return {"ok": False, "code": 0, "body": "", "error": "empty phone"}

    broadcast = broadcast_name or f"{settings.WATI_BROADCAST_PREFIX}_{template_name}"
    url = f"{settings.WATI_API_URL.rstrip('/')}/api/v1/sendTemplateMessages"
    payload = {
        "template_name": template_name,
        "broadcast_name": broadcast,
        "receivers": [
            {
                "whatsappNumber": clean_phone,
                # WATI rejects the whole send if ANY parameter value is empty
                # ("not enough parameters"), so coerce blanks to a placeholder.
                "customParams": [
                    {"name": k, "value": (("" if v is None else str(v)).strip() or "-")}
                    for k, v in params.items()
                ],
            }
        ],
    }

    try:
        resp = httpx.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json", "Authorization": _auth_header()},
            timeout=30,
        )
        code = resp.status_code
        body = resp.text
        ok = 200 <= code < 300
        # WATI sometimes returns 200 with {"result": false}
        try:
            data = resp.json()
            if isinstance(data, dict) and data.get("result") is False:
                ok = False
        except ValueError:
            data = {}
        error = "" if ok else f"HTTP {code} {body}"[:200]
        return {"ok": ok, "code": code, "body": body, "error": error}
    except httpx.HTTPError as exc:
        return {"ok": False, "code": 0, "body": "", "error": str(exc)}


# --- Template-specific helpers (param order/names match the approved templates) ---

def send_unassigned_notification(phone: str, ctx: dict[str, str]) -> dict[str, Any]:
    """`unassigned_lesson_notification` — a lesson is open for the pool."""
    return send_template_message(
        phone,
        settings.WATI_TEMPLATE_UNASSIGNED,
        {
            "urgency": ctx.get("urgency", ""),
            "course_name": ctx.get("course_name", ""),
            "lesson_id": ctx.get("lesson_code", ""),
            "date": ctx.get("date", ""),
            "start_time": ctx.get("start_time", ""),
            "end_time": ctx.get("end_time", ""),
            "school": ctx.get("school_name", ""),
        },
    )


def send_confirmation(phone: str, ctx: dict[str, str]) -> dict[str, Any]:
    """`tutor_confirmation_extra_info` — confirmed assignment + material link."""
    return send_template_message(
        phone,
        settings.WATI_TEMPLATE_CONFIRMATION,
        {
            "name": ctx.get("tutor_name", ""),
            "course_name": ctx.get("course_name", ""),
            "date": ctx.get("date", ""),
            "start_time": ctx.get("start_time", ""),
            "end_time": ctx.get("end_time", ""),
            "link": ctx.get("lesson_material_link") or "Materials will be shared separately",
        },
    )


def send_admin_cancellation(admin_phone: str, ctx: dict[str, str]) -> dict[str, Any]:
    """`tutor_cancellation_or_reschedule_admin_reminder` — alert the admin."""
    return send_template_message(
        admin_phone,
        settings.WATI_TEMPLATE_CANCEL_ADMIN,
        {
            "tutor_name": ctx.get("tutor_name", ""),
            "lesson_id": ctx.get("lesson_code", ""),
            "course_name": ctx.get("course_name", ""),
            "date": ctx.get("date", ""),
            "start_time": ctx.get("start_time", ""),
            "end_time": ctx.get("end_time", ""),
            "cancel_or_reschedule": ctx.get("intent", ""),
        },
    )
