"""Finances — read-only financial hub + monthly snapshot engine.

Endpoints
---------
GET  /finances/months            — available snapshot periods
GET  /finances/teacher-earnings  — salary data for a month or overall
GET  /finances/course-financials — P/L data for a month or overall
POST /finances/snapshot          — compute & upsert snapshots for a month
"""

from __future__ import annotations

from datetime import date
from calendar import monthrange

from fastapi import APIRouter, Depends, HTTPException, Query
from postgrest import SyncPostgrestClient

from app.api.deps import get_db

router = APIRouter(prefix="/finances", tags=["finances"])


# ── helpers ──────────────────────────────────────────────────────────────────

def _month_range(year: int, month: int) -> tuple[str, str]:
    """Return (start_date, end_date) ISO strings for the given month."""
    _, last_day = monthrange(year, month)
    return f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last_day:02d}"


# ── read endpoints ───────────────────────────────────────────────────────────

@router.get("/months")
def list_months(db: SyncPostgrestClient = Depends(get_db)):
    """Return distinct (year, month) pairs that have snapshot data from either table."""
    try:
        teacher_rows = (
            db.table("teacher_salary_snapshots")
            .select("year, month")
            .order("year", desc=True)
            .order("month", desc=True)
            .execute()
            .data or []
        )
        course_rows = (
            db.table("course_financial_snapshots")
            .select("year, month")
            .order("year", desc=True)
            .order("month", desc=True)
            .execute()
            .data or []
        )
        seen: set[tuple[int, int]] = set()
        result = []
        for rows in (teacher_rows, course_rows):
            for r in rows:
                key = (r["year"], r["month"])
                if key not in seen:
                    seen.add(key)
                    result.append({"year": r["year"], "month": r["month"]})
        result.sort(key=lambda item: (item["year"], item["month"]), reverse=True)
        return result
    except Exception:
        return []


@router.get("/teacher-earnings")
def teacher_earnings(
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
    db: SyncPostgrestClient = Depends(get_db),
):
    """Return teacher salary rows. Without params returns overall totals."""
    if year is not None and month is not None:
        rows = (
            db.table("teacher_salary_snapshots")
            .select("*")
            .eq("year", year)
            .eq("month", month)
            .order("total_payout", desc=True)
            .execute()
            .data or []
        )
        total = sum(r.get("total_payout", 0) or 0 for r in rows)
        return {"year": year, "month": month, "teachers": rows, "total": total}

    # Overall: aggregate across all months per teacher
    rows = (
        db.table("teacher_salary_snapshots")
        .select("teacher_id, teacher_name, tutor_hours, ta_hours, tutor_payout, ta_payout, total_payout, lessons_count")
        .order("teacher_name")
        .execute()
        .data or []
    )
    agg: dict[str, dict] = {}
    for r in rows:
        tid = r["teacher_id"]
        if tid not in agg:
            agg[tid] = {
                "teacher_id": tid,
                "teacher_name": r["teacher_name"],
                "tutor_hours": 0, "ta_hours": 0,
                "tutor_payout": 0, "ta_payout": 0,
                "total_payout": 0, "lessons_count": 0,
            }
        a = agg[tid]
        a["tutor_hours"] += float(r.get("tutor_hours") or 0)
        a["ta_hours"] += float(r.get("ta_hours") or 0)
        a["tutor_payout"] += float(r.get("tutor_payout") or 0)
        a["ta_payout"] += float(r.get("ta_payout") or 0)
        a["total_payout"] += float(r.get("total_payout") or 0)
        a["lessons_count"] += int(r.get("lessons_count") or 0)
    teachers = sorted(agg.values(), key=lambda t: t["total_payout"], reverse=True)
    total = sum(t["total_payout"] for t in teachers)
    return {"year": None, "month": None, "teachers": teachers, "total": total}


@router.get("/course-financials")
def course_financials(
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
    db: SyncPostgrestClient = Depends(get_db),
):
    """Return course P/L rows. Without params returns overall totals."""
    if year is not None and month is not None:
        rows = (
            db.table("course_financial_snapshots")
            .select("*")
            .eq("year", year)
            .eq("month", month)
            .order("profit_loss", desc=True)
            .execute()
            .data or []
        )
        total_income = sum(r.get("total_income", 0) or 0 for r in rows)
        total_expenses = sum(r.get("total_expenses", 0) or 0 for r in rows)
        return {
            "year": year, "month": month,
            "courses": rows,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "profit_loss": total_income - total_expenses,
        }

    # Overall: aggregate across all months per course
    rows = (
        db.table("course_financial_snapshots")
        .select("course_id, course_name, school_name, total_income, total_expenses, profit_loss, lessons_count")
        .order("course_name")
        .execute()
        .data or []
    )
    agg: dict[str, dict] = {}
    for r in rows:
        cid = r["course_id"]
        if cid not in agg:
            agg[cid] = {
                "course_id": cid,
                "course_name": r["course_name"],
                "school_name": r.get("school_name"),
                "total_income": 0, "total_expenses": 0,
                "profit_loss": 0, "lessons_count": 0,
            }
        a = agg[cid]
        a["total_income"] += float(r.get("total_income") or 0)
        a["total_expenses"] += float(r.get("total_expenses") or 0)
        a["profit_loss"] += float(r.get("profit_loss") or 0)
        a["lessons_count"] += int(r.get("lessons_count") or 0)
    courses = sorted(agg.values(), key=lambda c: c["profit_loss"], reverse=True)
    total_income = sum(c["total_income"] for c in courses)
    total_expenses = sum(c["total_expenses"] for c in courses)
    for c in courses:
        c["profit_loss_pct"] = (
            round(100 * c["profit_loss"] / c["total_income"], 2)
            if c["total_income"] > 0 else None
        )
    return {
        "year": None, "month": None,
        "courses": courses,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "profit_loss": total_income - total_expenses,
    }


# ── snapshot calculation ────────────────────────────────────────────────────

@router.post("/snapshot")
def compute_snapshot(
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
    db: SyncPostgrestClient = Depends(get_db),
):
    """Compute and upsert monthly snapshots. Defaults to previous month."""
    today = date.today()
    if year is None or month is None:
        # Default: previous month
        if today.month == 1:
            year, month = today.year - 1, 12
        else:
            year, month = today.year, today.month - 1

    start, end = _month_range(year, month)

    # ── teacher snapshots ────────────────────────────────────────────────
    lessons = (
        db.table("lessons")
        .select("id, teacher_id, role, start_time, end_time, date")
        .eq("status", "Completed")
        .gte("date", start)
        .lte("date", end)
        .not_.is_("teacher_id", "null")
        .execute()
        .data or []
    )

    # Fetch teacher rates
    teachers_raw = (
        db.table("teachers")
        .select("teacher_id, teacher_name, tutor_rate, ta_rate")
        .execute()
        .data or []
    )
    t_map = {t["teacher_id"]: t for t in teachers_raw}

    # Aggregate hours per teacher
    teacher_agg: dict[str, dict] = {}
    for l in lessons:
        tid = l["teacher_id"]
        if not tid or tid not in t_map:
            continue
        if l.get("start_time") and l.get("end_time"):
            # Parse time strings "HH:MM:SS" or "HH:MM"
            st = str(l["start_time"])
            et = str(l["end_time"])
            try:
                sh, sm = map(int, st[:5].split(":"))
                eh, em = map(int, et[:5].split(":"))
                hours = ((eh * 60 + em) - (sh * 60 + sm)) / 60.0
            except (ValueError, IndexError):
                hours = 0
        else:
            hours = 0

        if hours <= 0:
            continue

        if tid not in teacher_agg:
            t = t_map[tid]
            teacher_agg[tid] = {
                "teacher_id": tid,
                "teacher_name": t.get("teacher_name", tid),
                "tutor_hours": 0.0, "ta_hours": 0.0,
                "tutor_rate": float(t.get("tutor_rate") or 0),
                "ta_rate": float(t.get("ta_rate") or 0),
                "lessons_count": 0,
            }
        a = teacher_agg[tid]
        role = (l.get("role") or "").lower()
        if "teaching assistant" in role or "ta" == role:
            a["ta_hours"] += hours
        else:
            a["tutor_hours"] += hours
        a["lessons_count"] += 1

    # Upsert teacher snapshots
    teacher_rows = []
    for a in teacher_agg.values():
        a["tutor_payout"] = round(a["tutor_hours"] * a["tutor_rate"], 2)
        a["ta_payout"] = round(a["ta_hours"] * a["ta_rate"], 2)
        a["total_payout"] = a["tutor_payout"] + a["ta_payout"]
        teacher_rows.append(a)

    for tr in teacher_rows:
        payload = {
            "teacher_id": tr["teacher_id"],
            "teacher_name": tr["teacher_name"],
            "year": year, "month": month,
            "tutor_hours": tr["tutor_hours"],
            "ta_hours": tr["ta_hours"],
            "tutor_rate": tr["tutor_rate"],
            "ta_rate": tr["ta_rate"],
            "tutor_payout": tr["tutor_payout"],
            "ta_payout": tr["ta_payout"],
            "total_payout": tr["total_payout"],
            "lessons_count": tr["lessons_count"],
        }
        try:
            (
                db.table("teacher_salary_snapshots")
                .upsert(payload, on_conflict="teacher_id,year,month")
                .execute()
            )
        except Exception:
            pass

    # ── course snapshots ─────────────────────────────────────────────────
    # Fetch completed lessons with course + income + expenses
    course_lessons = (
        db.table("lessons")
        .select("id, course_id, lesson_income, miscellaneous_expenses, teacher_id, role, start_time, end_time")
        .eq("status", "Completed")
        .gte("date", start)
        .lte("date", end)
        .not_.is_("course_id", "null")
        .execute()
        .data or []
    )

    # Fetch courses for revenue_per_lesson
    courses_raw = (
        db.table("courses")
        .select("course_id, course_name, school_id, revenue_per_lesson")
        .execute()
        .data or []
    )
    c_map = {c["course_id"]: c for c in courses_raw}

    # Fetch schools for school_name
    schools_raw = (
        db.table("schools")
        .select("school_id, school_name")
        .execute()
        .data or []
    )
    s_map = {s["school_id"]: s.get("school_name") for s in schools_raw}

    # Aggregate per course
    course_agg: dict[str, dict] = {}
    for l in course_lessons:
        cid = l["course_id"]
        if not cid or cid not in c_map:
            continue

        if cid not in course_agg:
            c = c_map[cid]
            course_agg[cid] = {
                "course_id": cid,
                "course_name": c.get("course_name", cid),
                "school_name": s_map.get(c.get("school_id"), ""),
                "total_income": 0.0, "total_expenses": 0.0,
                "lessons_count": 0,
            }
        a = course_agg[cid]

        # Income: lesson_income or fallback to course revenue_per_lesson
        income = l.get("lesson_income")
        if income is None or income == 0:
            income = float(c_map[cid].get("revenue_per_lesson") or 0)
        else:
            income = float(income)
        a["total_income"] += income

        # Expenses: teacher payout + misc expenses
        payout = 0.0
        if l.get("start_time") and l.get("end_time") and l.get("teacher_id"):
            st = str(l["start_time"])
            et = str(l["end_time"])
            try:
                sh, sm = map(int, st[:5].split(":"))
                eh, em = map(int, et[:5].split(":"))
                hours = ((eh * 60 + em) - (sh * 60 + sm)) / 60.0
            except (ValueError, IndexError):
                hours = 0
            tid = l["teacher_id"]
            if tid in t_map and hours > 0:
                t = t_map[tid]
                role = (l.get("role") or "").lower()
                rate = float(t.get("ta_rate") or 0) if ("teaching assistant" in role or "ta" == role) else float(t.get("tutor_rate") or 0)
                payout = hours * rate

        misc = float(l.get("miscellaneous_expenses") or 0)
        a["total_expenses"] += payout + misc
        a["lessons_count"] += 1

    # Upsert course snapshots
    course_rows = []
    for a in course_agg.values():
        a["profit_loss"] = round(a["total_income"] - a["total_expenses"], 2)
        a["profit_loss_pct"] = (
            round(100 * a["profit_loss"] / a["total_income"], 2)
            if a["total_income"] > 0 else None
        )
        course_rows.append(a)

    for cr in course_rows:
        payload = {
            "course_id": cr["course_id"],
            "course_name": cr["course_name"],
            "school_name": cr["school_name"],
            "year": year, "month": month,
            "total_income": cr["total_income"],
            "total_expenses": cr["total_expenses"],
            "profit_loss": cr["profit_loss"],
            "profit_loss_pct": cr["profit_loss_pct"],
            "lessons_count": cr["lessons_count"],
        }
        try:
            (
                db.table("course_financial_snapshots")
                .upsert(payload, on_conflict="course_id,year,month")
                .execute()
            )
        except Exception:
            pass

    return {
        "status": "ok",
        "year": year,
        "month": month,
        "teachers": len(teacher_rows),
        "courses": len(course_rows),
    }
