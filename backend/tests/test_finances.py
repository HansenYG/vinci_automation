from types import SimpleNamespace

from app.api.routes.finances import compute_snapshot, list_months


class FakeQuery:
    def __init__(self, rows, table_name=""):
        self.rows = rows
        self.table_name = table_name
        self.filters = []
        self.writes = []
        self.not_ = self

    def select(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def gte(self, *args, **kwargs):
        return self

    def lte(self, *args, **kwargs):
        return self

    def not_(self):
        return self

    def is_(self, *args, **kwargs):
        return self

    def __getattr__(self, name):
        if name == "is_":
            return self.is_
        return self

    def upsert(self, payload, on_conflict=None):
        self.writes.append(payload)
        return self

    def execute(self):
        if self.table_name == "lessons" and any(column == "status" and value == "Completed" for column, value in self.filters):
            rows = [row for row in self.rows if row.get("status") == "Completed"]
            return SimpleNamespace(data=rows)
        if self.writes:
            return SimpleNamespace(data=self.writes)
        return SimpleNamespace(data=self.rows)


class FakeDB:
    def __init__(self, teacher_rows=None, course_rows=None, lessons=None, teachers=None, schools=None, courses=None):
        self.teacher_rows = teacher_rows or []
        self.course_rows = course_rows or []
        self.lessons = lessons or []
        self.teachers = teachers or []
        self.schools = schools or []
        self.courses = courses or self.course_rows
        self.tables = {
            "teacher_salary_snapshots": FakeQuery(self.teacher_rows, "teacher_salary_snapshots"),
            "course_financial_snapshots": FakeQuery(self.course_rows, "course_financial_snapshots"),
            "lessons": FakeQuery(self.lessons, "lessons"),
            "teachers": FakeQuery(self.teachers, "teachers"),
            "courses": FakeQuery(self.courses, "courses"),
            "schools": FakeQuery(self.schools, "schools"),
        }

    def table(self, table_name):
        return self.tables[table_name]


def test_list_months_unions_teacher_and_course_snapshot_periods():
    db = FakeDB(
        teacher_rows=[{"year": 2024, "month": 2}],
        course_rows=[{"year": 2025, "month": 3}, {"year": 2024, "month": 1}],
    )

    months = list_months(db=db)

    assert months == [
        {"year": 2025, "month": 3},
        {"year": 2024, "month": 2},
        {"year": 2024, "month": 1},
    ]


def test_compute_snapshot_accepts_completed_lessons_with_case_variant_status():
    db = FakeDB(
        lessons=[
            {
                "id": "lesson-1",
                "teacher_id": "TCH-001",
                "course_id": "CRS-001",
                "role": "Tutor",
                "start_time": "10:00",
                "end_time": "12:00",
                "date": "2026-02-10",
                "status": "completed",
                "lesson_income": 1000,
                "miscellaneous_expenses": 100,
            }
        ],
        teachers=[
            {"teacher_id": "TCH-001", "teacher_name": "Ada", "tutor_rate": 350, "ta_rate": 200}
        ],
        courses=[
            {"course_id": "CRS-001", "course_name": "Math", "school_id": "SCH-001", "revenue_per_lesson": 1200}
        ],
        schools=[{"school_id": "SCH-001", "school_name": "North School"}],
    )

    result = compute_snapshot(year=2026, month=2, db=db)

    assert result["teachers"] == 1
    assert result["courses"] == 1
    assert db.tables["teacher_salary_snapshots"].writes[0]["total_payout"] == 700.0
    assert db.tables["course_financial_snapshots"].writes[0]["profit_loss"] == 200.0
