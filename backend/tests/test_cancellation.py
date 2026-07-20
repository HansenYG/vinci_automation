"""Tests for scheduling.handle_cancellation — tutor cancellation blindspot fix.

Covers:
  * cancel intent sets lessons.status to "Cancelled" (reschedule keeps OfferSent)
  * the cancelling tutor's offer is withdrawn and excluded from the re-blast
  * the admin WhatsApp notification fires when ADMIN_WHATSAPP is configured
  * a missing ADMIN_WHATSAPP is surfaced via admin_notify_skipped, never silent
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import scheduling

LESSON_ID = "lesson-1"
TEACHER_ID = "T1"
LESSON = {"id": LESSON_ID, "within_a_week": True, "lesson_code": "LESS-001"}


def _run(intent="cancel", admin_whatsapp="85200000000", send_ok=True):
    """Run handle_cancellation with mocked repos/wati/settings; return mocks."""
    repos = MagicMock()
    repos.get_lesson_view.return_value = dict(LESSON)
    repos.lesson_wati_context.return_value = {"lesson_code": "LESS-001"}
    repos.get_row.return_value = {"teacher_id": TEACHER_ID, "teacher_name": "Tutor One"}

    wati = MagicMock()
    wati.send_admin_cancellation.return_value = {
        "ok": send_ok,
        "error": "" if send_ok else "HTTP 500 boom",
    }

    settings = MagicMock()
    settings.ADMIN_WHATSAPP = admin_whatsapp

    with patch.object(scheduling, "repos", repos), \
         patch.object(scheduling, "wati", wati), \
         patch.object(scheduling, "settings", settings), \
         patch.object(scheduling, "blast_lesson", return_value={"sent": 3}) as blast:
        result = scheduling.handle_cancellation(MagicMock(), LESSON_ID, TEACHER_ID, intent)

    return result, repos, wati, blast


class TestStatusUpdate:
    def test_cancel_sets_status_cancelled(self):
        _, repos, _, _ = _run(intent="cancel")
        payload = repos.update_row.call_args[0][3]
        assert payload["status"] == "Cancelled"
        assert payload["teacher_id"] is None

    def test_reschedule_keeps_offersent(self):
        _, repos, _, _ = _run(intent="reschedule")
        payload = repos.update_row.call_args[0][3]
        assert payload["status"] == "OfferSent"

    def test_cancelling_tutor_offer_withdrawn(self):
        _, repos, _, _ = _run(intent="cancel")
        args = repos.set_offer_status.call_args[0]
        assert args[2] == TEACHER_ID
        assert args[3] == "withdrawn"


class TestAdminNotification:
    def test_admin_notified_when_configured(self):
        result, repos, wati, _ = _run(intent="cancel", admin_whatsapp="85200000000")
        wati.send_admin_cancellation.assert_called_once()
        call = wati.send_admin_cancellation.call_args[0]
        assert call[0] == "85200000000"
        assert call[1]["tutor_name"] == "Tutor One"
        assert call[1]["intent"] == "cancel"
        assert result["admin_notified"] is True
        events = [c[0][3] for c in repos.log_event.call_args_list]
        assert "admin_notified" in events

    def test_missing_admin_whatsapp_never_silent(self):
        result, repos, wati, _ = _run(intent="cancel", admin_whatsapp="")
        wati.send_admin_cancellation.assert_not_called()
        assert result["admin_notified"] is False
        skip_events = [
            c for c in repos.log_event.call_args_list
            if c[0][3] == "admin_notify_skipped"
        ]
        assert len(skip_events) == 1

    def test_failed_send_still_logged(self):
        result, repos, _, _ = _run(intent="cancel", send_ok=False)
        assert result["admin_notified"] is False
        notified = [
            c for c in repos.log_event.call_args_list
            if c[0][3] == "admin_notified"
        ]
        assert notified[0][0][4] == {"ok": False}


class TestReblast:
    def test_reblast_excludes_cancelling_tutor(self):
        _, _, _, blast = _run(intent="cancel")
        _, kwargs = blast.call_args
        assert kwargs["force_all"] is True
        assert kwargs["exclude_teacher_id"] == TEACHER_ID
