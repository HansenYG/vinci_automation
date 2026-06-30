"""Finances (design Phase 3) — scaffold only.

Endpoints are wired and documented so the frontend route exists, but the
calculations (teacher earnings per month, course income/expenses) are filled
in during Phase 3. `hourly_rate` already lives on courses for this.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/finances", tags=["finances"])

_NOT_YET = {"phase": 3, "status": "scaffolded", "detail": "Implemented in Phase 3."}


@router.get("/teacher-earnings")
def teacher_earnings():
    return _NOT_YET


@router.get("/course-financials")
def course_financials():
    return _NOT_YET
