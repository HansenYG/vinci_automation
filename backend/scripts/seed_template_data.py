"""Insert template seed data: 10 teachers, 5 courses, 20 lessons."""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("SUPABASE_URL", "https://zigzgzurmuplgcqsnnlv.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InppZ3pnenVybXVwbGdjcXNubmx2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4Mjc3NTIyMiwiZXhwIjoyMDk4MzUxMjIyfQ.8kQnHp4ZQGF-D2sG7pdJfLqQmxs77C8FFDyTrJv_5Ak")

from app.core.config import settings
from app.core.database import _build_headers
from postgrest import SyncPostgrestClient


def get_db():
    key = settings.SUPABASE_KEY or settings.SUPABASE_ANON_KEY
    return SyncPostgrestClient(
        f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1",
        headers=_build_headers(key),
    )


db = get_db()

# ── Teachers ────────────────────────────────────────────────────────────
teachers = [
    {"teacher_id": "TCH-001", "teacher_name": "Emily Chen", "email": "emily.chen@tutor.com", "whatsapp_number": "85291234501", "status": "Active", "tutor_rate": 350, "ta_rate": 200, "reliability_score": 4.8, "background": "Maths & Physics specialist, 5 yr experience"},
    {"teacher_id": "TCH-002", "teacher_name": "James Wong", "email": "james.wong@tutor.com", "whatsapp_number": "85291234502", "status": "Active", "tutor_rate": 300, "ta_rate": 180, "reliability_score": 4.5, "background": "Chemistry & Biology, PhD candidate"},
    {"teacher_id": "TCH-003", "teacher_name": "Sarah Patel", "email": "sarah.patel@tutor.com", "whatsapp_number": "85291234503", "status": "Active", "tutor_rate": 320, "ta_rate": 190, "reliability_score": 4.7, "background": "English Literature & Language, MA"},
    {"teacher_id": "TCH-004", "teacher_name": "Michael Liu", "email": "michael.liu@tutor.com", "whatsapp_number": "85291234504", "status": "Active", "tutor_rate": 280, "ta_rate": 160, "reliability_score": 4.3, "background": "History & Geography, BA"},
    {"teacher_id": "TCH-005", "teacher_name": "Aisha Khan", "email": "aisha.khan@tutor.com", "whatsapp_number": "85291234505", "status": "Active", "tutor_rate": 360, "ta_rate": 210, "reliability_score": 4.9, "background": "Computer Science & Robotics, MEng"},
    {"teacher_id": "TCH-006", "teacher_name": "David Park", "email": "david.park@tutor.com", "whatsapp_number": "85291234506", "status": "Active", "tutor_rate": 290, "ta_rate": 170, "reliability_score": 4.1, "background": "Economics & Business Studies, MBA"},
    {"teacher_id": "TCH-007", "teacher_name": "Lisa Thompson", "email": "lisa.thompson@tutor.com", "whatsapp_number": "85291234507", "status": "Active", "tutor_rate": 330, "ta_rate": 195, "reliability_score": 4.6, "background": "Music Theory & Piano, DipABRSM"},
    {"teacher_id": "TCH-008", "teacher_name": "Raj Sharma", "email": "raj.sharma@tutor.com", "whatsapp_number": "85291234508", "status": "Active", "tutor_rate": 340, "ta_rate": 200, "reliability_score": 4.4, "background": "Physics & Engineering, BEng"},
    {"teacher_id": "TCH-009", "teacher_name": "Yuki Tanaka", "email": "yuki.tanaka@tutor.com", "whatsapp_number": "85291234509", "status": "Active", "tutor_rate": 310, "ta_rate": 185, "reliability_score": 4.2, "background": "Japanese Language & Culture, native speaker"},
    {"teacher_id": "TCH-010", "teacher_name": "Maria Garcia", "email": "maria.garcia@tutor.com", "whatsapp_number": "85291234510", "status": "Active", "tutor_rate": 370, "ta_rate": 220, "reliability_score": 4.8, "background": "Spanish & French, MA Languages"},
]

for t in teachers:
    db.table("teachers").upsert(t, on_conflict="teacher_id").execute()
    print(f"  ✓ {t['teacher_id']} {t['teacher_name']}")

# ── Courses ─────────────────────────────────────────────────────────────
courses = [
    {"course_id": "ARW", "course_name": "Advanced Robotics Workshop", "course_topic": "STEM / Robotics", "revenue_per_lesson": 800},
    {"course_id": "IGP", "course_name": "IGCSE Physics", "course_topic": "Science / Physics", "revenue_per_lesson": 600},
    {"course_id": "ELT", "course_name": "English Literature", "course_topic": "Humanities / English", "revenue_per_lesson": 550},
    {"course_id": "CSC", "course_name": "Computer Science Club", "course_topic": "STEM / Computing", "revenue_per_lesson": 750},
    {"course_id": "MUS", "course_name": "Music Theory & Practice", "course_topic": "Arts / Music", "revenue_per_lesson": 650},
]

for c in courses:
    db.table("courses").upsert(c, on_conflict="course_id").execute()
    print(f"  ✓ {c['course_id']} {c['course_name']}")

# ── Lessons ─────────────────────────────────────────────────────────────
today = date.today()
lessons_data = [
    # Next 20 weekdays (Mon-Fri), alternating courses
    {"course_id": "ARW", "hour": 9, "min": 0, "duration": 120},
    {"course_id": "IGP", "hour": 11, "min": 0, "duration": 90},
    {"course_id": "ELT", "hour": 14, "min": 0, "duration": 60},
    {"course_id": "CSC", "hour": 16, "min": 0, "duration": 120},
    {"course_id": "MUS", "hour": 10, "min": 0, "duration": 90},
    {"course_id": "ARW", "hour": 13, "min": 0, "duration": 120},
    {"course_id": "IGP", "hour": 15, "min": 0, "duration": 90},
    {"course_id": "CSC", "hour": 9, "min": 0, "duration": 120},
    {"course_id": "ELT", "hour": 11, "min": 0, "duration": 60},
    {"course_id": "MUS", "hour": 14, "min": 0, "duration": 90},
    {"course_id": "ARW", "hour": 16, "min": 0, "duration": 120},
    {"course_id": "IGP", "hour": 9, "min": 0, "duration": 90},
    {"course_id": "CSC", "hour": 11, "min": 0, "duration": 120},
    {"course_id": "ELT", "hour": 14, "min": 0, "duration": 60},
    {"course_id": "MUS", "hour": 16, "min": 0, "duration": 90},
    {"course_id": "ARW", "hour": 10, "min": 0, "duration": 120},
    {"course_id": "IGP", "hour": 13, "min": 0, "duration": 90},
    {"course_id": "CSC", "hour": 15, "min": 0, "duration": 120},
    {"course_id": "ELT", "hour": 9, "min": 0, "duration": 60},
    {"course_id": "MUS", "hour": 11, "min": 0, "duration": 90},
]

def next_weekday(d, weekday=0):
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return d + timedelta(days=days_ahead)

start_date = next_weekday(today, 0)  # next Monday
if start_date <= today:
    start_date += timedelta(days=7)
from app.services.codes import next_lesson_code

course_map = {c["course_id"]: c["course_name"] for c in courses}

for i, spec in enumerate(lessons_data):
    d = start_date + timedelta(days=i)
    cid = spec["course_id"]
    cname = course_map[cid]
    h, m = spec["hour"], spec["min"]
    dur = spec["duration"]
    end_h = h + dur // 60
    end_m = m + dur % 60
    if end_m >= 60:
        end_h += 1
        end_m -= 60
    code = f"LES-{d.strftime('%Y%m%d')}-{h:02d}{m:02d}-{cid}"
    lesson = {
        "lesson_id": code,
        "date": d.isoformat(),
        "start_time": f"{h:02d}:{m:02d}",
        "end_time": f"{end_h:02d}:{end_m:02d}",
        "course_id": cid,
        "status": "Unassigned",
    }
    db.table("lessons").insert(lesson).execute()
    print(f"  ✓ {code} {cname} {d} {h:02d}:{m:02d}")

print("\nDone! 10 teachers, 5 courses, 20 lessons seeded.")
