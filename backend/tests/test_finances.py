from types import SimpleNamespace

from app.api.routes.finances import list_months


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def select(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=self.rows)


class FakeDB:
    def __init__(self, teacher_rows=None, course_rows=None):
        self.teacher_rows = teacher_rows or []
        self.course_rows = course_rows or []

    def table(self, table_name):
        if table_name == "teacher_salary_snapshots":
            return FakeQuery(self.teacher_rows)
        if table_name == "course_financial_snapshots":
            return FakeQuery(self.course_rows)
        raise AssertionError(f"unexpected table {table_name}")


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
