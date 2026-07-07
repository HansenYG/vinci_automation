"""Seed template data: 10 teachers, 5 courses, 20 lessons."""
import os, sys, requests
from datetime import date, timedelta

API = os.getenv("API_BASE", "https://vinci-automation-api-beta.onrender.com")
SUPABASE_URL = "https://zigzgzurmuplgcqsnnlv.supabase.co"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InppZ3pnenVybXVwbGdjcXNubmx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI3NzUyMjIsImV4cCI6MjA5ODM1MTIyMn0.cGkHBdME80jDYDGRV_IBcGVp0k7IyCzxWSZOLqsZcIQ"
TIMEOUT = 15


def get_jwt(email, password):
    r = requests.post(f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
                      json={"email": email, "password": password},
                      headers={"apikey": ANON_KEY}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()["access_token"]


def api_post(path, data, token):
    r = requests.post(f"{API}/api{path}", json=data,
                      headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT)
    if r.status_code == 409:
        return {}
    r.raise_for_status()
    return r.json()


teachers = [
    {"teacher_name": "Emily Chen", "whatsapp_number": "85291234501", "status": "Active"},
    {"teacher_name": "James Wong", "whatsapp_number": "85291234502", "status": "Active"},
    {"teacher_name": "Sarah Patel", "whatsapp_number": "85291234503", "status": "Active"},
    {"teacher_name": "Michael Liu", "whatsapp_number": "85291234504", "status": "Active"},
    {"teacher_name": "Aisha Khan", "whatsapp_number": "85291234505", "status": "Active"},
    {"teacher_name": "David Park", "whatsapp_number": "85291234506", "status": "Active"},
    {"teacher_name": "Lisa Thompson", "whatsapp_number": "85291234507", "status": "Active"},
    {"teacher_name": "Raj Sharma", "whatsapp_number": "85291234508", "status": "Active"},
    {"teacher_name": "Yuki Tanaka", "whatsapp_number": "85291234509", "status": "Active"},
    {"teacher_name": "Maria Garcia", "whatsapp_number": "85291234510", "status": "Active"},
]

courses_list = [
    {"course_name": "Advanced Robotics Workshop", "course_topic": "STEM / Robotics", "revenue_per_lesson": 800},
    {"course_name": "IGCSE Physics", "course_topic": "Science / Physics", "revenue_per_lesson": 600},
    {"course_name": "English Literature", "course_topic": "Humanities / English", "revenue_per_lesson": 550},
    {"course_name": "Computer Science Club", "course_topic": "STEM / Computing", "revenue_per_lesson": 750},
    {"course_name": "Music Theory & Practice", "course_topic": "Arts / Music", "revenue_per_lesson": 650},
]

lessons_spec = [
    (0, 9, 0, 0), (0, 11, 0, 1), (0, 14, 0, 2), (0, 16, 0, 3), (1, 10, 0, 4),
    (1, 13, 0, 0), (1, 15, 0, 1), (2, 9, 0, 3), (2, 11, 0, 2), (2, 14, 0, 4),
    (3, 16, 0, 0), (3, 9, 0, 1), (3, 11, 0, 3), (4, 14, 0, 2), (4, 16, 0, 4),
    (4, 10, 0, 0), (5, 13, 0, 1), (5, 15, 0, 3), (5, 9, 0, 2), (5, 11, 0, 4),
]


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/seed_template_data.py <email> <password>")
        sys.exit(1)

    email, pw = sys.argv[1], sys.argv[2]
    print("Logging in...", end=" ", flush=True)
    token = get_jwt(email, pw)
    print("OK\n")

    for t in teachers:
        result = api_post("/teachers", t, token)
        tid = result.get("teacher_id", "?")
        print(f"  TCH {tid}: {t['teacher_name']}")

    print()
    course_ids = []
    for c in courses_list:
        result = api_post("/courses", c, token)
        cid = result.get("course_id", "?")
        course_ids.append(cid)
        print(f"  CRS {cid}: {c['course_name']}")

    print()
    today = date.today()
    monday = today + timedelta(days=(7 - today.weekday()) % 7 or 7)
    for day_off, h, m, ci in lessons_spec:
        d = monday + timedelta(days=day_off)
        cid = course_ids[ci]
        eh, em = h + 1, m + 30
        if em >= 60:
            eh += 1; em -= 60
        lesson = {"date": d.isoformat(), "start_time": f"{h:02d}:{m:02d}",
                  "end_time": f"{eh:02d}:{em:02d}", "course_id": cid, "status": "Unassigned"}
        result = api_post("/lessons", lesson, token)
        lid = result.get("lesson_id") or result.get("id", "?")
        print(f"  LES {lid}: {d} {h:02d}:{m:02d}-{eh:02d}:{em:02d} {cid}")

    print("\nDone.")


if __name__ == "__main__":
    main()
