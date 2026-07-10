"""Regression tests for repos.teachers_by_phone NameError and log_event fix.

Bug 1: teachers_by_phone fallback called repos.list_rows() which raised
       NameError because the module cannot self-reference by name.
Bug 2: log_event signature had school_id before detail, but all callers
       passed detail dicts positionally — causing silent insert failures
       on the lesson_events table (no school_id column exists).

These tests mock the Supabase client to exercise the fixed code paths
without needing a running database.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import repos


# ---------------------------------------------------------------------------
# Mock Supabase client
# ---------------------------------------------------------------------------

def _make_mock_db(teachers: list[dict] | None = None):
    """Build a mock SyncPostgrestClient that returns *teachers* for any
    ``db.table("teachers").select("*")`` query."""
    db = MagicMock()

    teacher_rows = teachers or []

    # .table("teachers").select("*").eq("whatsapp_number", target).execute()
    eq_mock = MagicMock()
    eq_mock.execute.return_value = MagicMock(data=teacher_rows)
    select_mock = MagicMock()
    select_mock.eq.return_value = eq_mock
    db.table.return_value.select.return_value = select_mock

    return db, select_mock


# ---------------------------------------------------------------------------
# teachers_by_phone tests
# ---------------------------------------------------------------------------

class TestTeachersByPhone:
    """Verify the NameError in the fallback path is fixed."""

    def _make_teacher(self, tid: str, phone: str) -> dict:
        return {"teacher_id": tid, "teacher_name": f"Tutor {tid}", "whatsapp_number": phone}

    def test_exact_match_returns_immediately(self):
        """When the exact DB match hits, no fallback is needed."""
        t = self._make_teacher("T1", "85252408480")
        db, select_mock = _make_mock_db([t])

        # Exact match returns the row
        eq_mock = select_mock.eq.return_value
        eq_mock.execute.return_value = MagicMock(data=[t])

        result = repos.teachers_by_phone(db, "85252408480")
        assert len(result) == 1
        assert result[0]["teacher_id"] == "T1"

    def test_fallback_does_not_raise_name_error(self):
        """The core regression: when exact match fails, the fallback path
        must call list_rows() (not repos.list_rows()) and not crash."""
        t = self._make_teacher("T2", "12345678")       # stored with no country code
        db, select_mock = _make_mock_db([t])

        # Exact match returns empty (WATI sends 85212345678, stored is 12345678)
        eq_mock = select_mock.eq.return_value
        eq_mock.execute.return_value = MagicMock(data=[])

        # The fallback calls list_rows which queries all teachers
        all_teachers = db.table.return_value.select.return_value
        all_teachers.execute.return_value = MagicMock(data=[t])

        # This should NOT raise NameError
        result = repos.teachers_by_phone(db, "85212345678")
        assert len(result) == 1
        assert result[0]["teacher_id"] == "T2"

    def test_fallback_suffix_match_stored_in_target(self):
        """Stored '52408480' is a substring of target '85252408480'."""
        t = self._make_teacher("T3", "52408480")
        db, select_mock = _make_mock_db([t])

        eq_mock = select_mock.eq.return_value
        eq_mock.execute.return_value = MagicMock(data=[])

        all_teachers = db.table.return_value.select.return_value
        all_teachers.execute.return_value = MagicMock(data=[t])

        result = repos.teachers_by_phone(db, "85252408480")
        assert len(result) == 1
        assert result[0]["teacher_id"] == "T3"

    def test_fallback_suffix_match_target_in_stored(self):
        """Target '12345678' is a substring of stored '85212345678'."""
        t = self._make_teacher("T4", "85212345678")
        db, select_mock = _make_mock_db([t])

        eq_mock = select_mock.eq.return_value
        eq_mock.execute.return_value = MagicMock(data=[])

        all_teachers = db.table.return_value.select.return_value
        all_teachers.execute.return_value = MagicMock(data=[t])

        result = repos.teachers_by_phone(db, "12345678")
        assert len(result) == 1
        assert result[0]["teacher_id"] == "T4"

    def test_empty_phone_returns_empty(self):
        db, _ = _make_mock_db([])
        result = repos.teachers_by_phone(db, "")
        assert result == []

    def test_no_match_returns_empty(self):
        t = self._make_teacher("T5", "11111111")
        db, select_mock = _make_mock_db([t])

        eq_mock = select_mock.eq.return_value
        eq_mock.execute.return_value = MagicMock(data=[])

        all_teachers = db.table.return_value.select.return_value
        all_teachers.execute.return_value = MagicMock(data=[t])

        result = repos.teachers_by_phone(db, "99999999")
        assert result == []


# ---------------------------------------------------------------------------
# log_event tests
# ---------------------------------------------------------------------------

class TestLogEvent:
    """Verify log_event correctly passes detail dict and doesn't fail
    on the lesson_events table (no school_id column)."""

    def test_log_event_with_detail_dict(self):
        """The common call pattern: log_event(db, lid, tid, 'blast', {...})."""
        db = MagicMock()
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])

        repos.log_event(db, "lesson-uuid", "T1", "blast", {"ok": True, "phone": "123"})

        # Verify the insert was called with correct payload
        insert_call = db.table.return_value.insert
        payload = insert_call.call_args[0][0]
        assert payload["event_type"] == "blast"
        assert payload["detail"] == {"ok": True, "phone": "123"}
        assert "school_id" not in payload, "school_id should not be in payload"

    def test_log_event_with_empty_detail(self):
        """Accept events pass {} — detail should be {}, no school_id."""
        db = MagicMock()
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])

        repos.log_event(db, "lesson-uuid", "T1", "accept", {})

        payload = db.table.return_value.insert.call_args[0][0]
        assert payload["detail"] == {}
        assert "school_id" not in payload

    def test_log_event_no_detail(self):
        """Calling with no detail arg — detail defaults to {}."""
        db = MagicMock()
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])

        repos.log_event(db, "lesson-uuid", "T1", "accept")

        payload = db.table.return_value.insert.call_args[0][0]
        assert payload["detail"] == {}

    def test_log_event_db_error_is_swallowed(self):
        """DB insert failure must not raise — it's non-fatal."""
        db = MagicMock()
        db.table.return_value.insert.return_value.execute.side_effect = Exception("column school_id does not exist")

        # Should NOT raise
        repos.log_event(db, "lesson-uuid", "T1", "blast", {"ok": True})


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
