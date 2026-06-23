"""Urgency + schedule-colour rules (kept identical to the SQL view and the
original Apps Scripts: 'urgent' when a lesson is within URGENT_WINDOW_DAYS)."""

from __future__ import annotations

from datetime import date, datetime

from app.core.config import settings


def _as_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return datetime.fromisoformat(str(value)[:10]).date()


def within_a_week(lesson_date) -> bool:
    return (_as_date(lesson_date) - date.today()).days <= settings.URGENT_WINDOW_DAYS


def urgency_label(lesson_date) -> str:
    """'urgent' if the class is within the window, else 'new class'
    (the exact wording the WATI templates expect)."""
    return "urgent" if within_a_week(lesson_date) else "new class"


def schedule_color(status: str, lesson_date) -> str:
    """Mirror of the lesson_schedule view's colour logic."""
    if status == "cancelled":
        return "grey"
    if status == "completed":
        return "blue"
    if status == "assigned":
        return "green"
    if status == "unassigned" and within_a_week(lesson_date):
        return "red"
    return "yellow"
