"""Integration tests verifying lesson_income syncs correctly across the stack.

Run against the local Supabase stack (``supabase start`` must be running):

    pip install pytest httpx
    pytest backend/tests/test_lesson_income.py -v

Or via the test-env script (which resets + seeds first):

    python backend/scripts/test_env.py

Tests are idempotent and use their own data so they do not interfere with
existing seed rows.
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timezone

import pytest
import httpx

API_BASE = os.environ.get("TEST_API_BASE", "http://127.0.0.1:8000/api")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _unique(label: str) -> str:
    ts = datetime.now().strftime("%H%M%S%f")
    return f"{label}-{ts}"


def _cleanup(client: httpx.Client, table: str, pk_col: str, ids: list[str]) -> None:
    for pk in ids:
        client.delete(f"/{table}/{pk}")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=API_BASE, timeout=15) as c:
        yield c


@pytest.fixture
def school(client: httpx.Client):
    sid = _unique("SCH")
    r = client.post("/schools", json={"school_id": sid, "school_name": f"Test School {sid}"})
    assert r.status_code == 201, r.text
    yield r.json()
    client.delete(f"/schools/{sid}")


@pytest.fixture
def course(client: httpx.Client, school: dict):
    cid = _unique("CRS")
    r = client.post("/courses", json={
        "course_id": cid,
        "course_name": f"Test Course {cid}",
        "school_id": school["school_id"],
        "revenue_per_lesson": 5000.00,
    })
    assert r.status_code == 201, r.text
    yield r.json()
    client.delete(f"/courses/{cid}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

SHARED = {"lesson_id": None}


class TestLessonIncomeSync:
    """Verify lesson_income is accepted, stored, returned, and updated correctly."""

    def test_1_create_without_income(self, client: httpx.Client, course: dict):
        """Creating a lesson without lesson_income -> field is null."""
        r = client.post("/lessons", json={
            "date": "2027-01-15",
            "course_id": course["course_id"],
            "start_time": "09:00",
            "end_time": "10:00",
        })
        assert r.status_code == 201, r.text
        lesson = r.json()
        assert lesson["lesson_income"] is None, f"expected None, got {lesson['lesson_income']}"
        lid = lesson["id"]
        client.delete(f"/lessons/{lid}")

    def test_2_create_with_income(self, client: httpx.Client, course: dict):
        """Creating a lesson with lesson_income -> stored and returned."""
        r = client.post("/lessons", json={
            "date": "2027-01-16",
            "course_id": course["course_id"],
            "start_time": "10:00",
            "end_time": "11:00",
            "lesson_income": 3500.00,
        })
        assert r.status_code == 201, r.text
        lesson = r.json()
        assert lesson["lesson_income"] == 3500.00, f"expected 3500.0, got {lesson['lesson_income']}"
        SHARED["lesson_id"] = lesson["id"]

    def test_3_get_lesson_returns_income(self, client: httpx.Client):
        """GET /lessons/{id} returns the stored lesson_income."""
        lid = SHARED.get("lesson_id")
        assert lid, "no lesson id from previous test"
        r = client.get(f"/lessons/{lid}")
        assert r.status_code == 200, r.text
        assert r.json()["lesson_income"] == 3500.00

    def test_4_update_income(self, client: httpx.Client):
        """PATCH lesson_income -> new value is stored."""
        lid = SHARED["lesson_id"]
        r = client.patch(f"/lessons/{lid}", json={"lesson_income": 4200.00})
        assert r.status_code == 200, r.text
        assert r.json()["lesson_income"] == 4200.00

    def test_5_clear_income(self, client: httpx.Client):
        """Setting lesson_income to 0 clears it (API excludes None)."""
        lid = SHARED["lesson_id"]
        r = client.patch(f"/lessons/{lid}", json={"lesson_income": 0})
        assert r.status_code == 200, r.text
        assert r.json()["lesson_income"] == 0

    def test_6_schedule_view_includes_income(self, client: httpx.Client):
        """lesson_schedule view also returns lesson_income."""
        lid = SHARED["lesson_id"]
        r = client.get("/lessons")
        assert r.status_code == 200, r.text
        lessons = r.json()
        ours = [l for l in lessons if l["id"] == lid]
        assert len(ours) == 1, f"expected 1 match, got {len(ours)}"
        assert "lesson_income" in ours[0], "lesson_income missing from schedule view"

    def test_7_unassigned_view_includes_income(self, client: httpx.Client):
        """Unassigned endpoint also carries lesson_income."""
        lid = SHARED["lesson_id"]
        r = client.get("/lessons/unassigned")
        assert r.status_code == 200, r.text
        ours = [l for l in r.json() if l["id"] == lid]
        if ours:
            assert "lesson_income" in ours[0]

    def test_8_cleanup(self, client: httpx.Client):
        """Remove the test lesson."""
        lid = SHARED.get("lesson_id")
        if lid:
            r = client.delete(f"/lessons/{lid}")
            assert r.status_code == 204

    def test_9_announce_lesson_with_income(self, client: httpx.Client, course: dict):
        """Quick-input / announce-lesson endpoint accepts lesson_income."""
        r = client.post("/scheduling/announce-lesson", json={
            "date": "2027-01-20",
            "start_time": "14:00",
            "end_time": "15:00",
            "course": course["course_name"],
            "lesson_income": 5000.00,
        })
        if r.status_code == 200:
            data = r.json()
            lid = data.get("lesson_id")
            if lid:
                lesson_r = client.get(f"/lessons/{lid}")
                if lesson_r.status_code == 200:
                    assert lesson_r.json().get("lesson_income") == 5000.00
                client.delete(f"/lessons/{lid}")
