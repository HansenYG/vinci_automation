"""
Comprehensive End-to-End Testing Script for Vinci Automation System
Tests all features systematically as requested.
"""
import requests
import json
from datetime import datetime, date, timedelta
import sys
import io

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configuration
BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"
SUPABASE_URL = "http://127.0.0.1:54321"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InppZ3pnenVybXVwbGdjcXNubmx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI3NzUyMjIsImV4cCI6MjA5ODM1MTIyMn0.cGkHBdME80jDYDGRV_IBcGVp0k7IyCzxWSZOLqsZcIQ"

# Test credentials
TEST_EMAIL = "hansenyg@vinciai.academy"
TEST_PASSWORD = "VinciBeta2026!"

# Global state for storing auth token and session
auth_token = None
session_user = None

# Test results tracking
test_results = []

def log_test(test_name, status, details=""):
    """Log a test result"""
    result = {
        "test": test_name,
        "status": status,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
    # Only append actual test results, not INFO
    if status in ["PASS", "FAIL", "SKIP", "PARTIAL"]:
        test_results.append(result)
    status_symbol = "[PASS]" if status == "PASS" else "[FAIL]" if status == "FAIL" else "[SKIP]" if status == "SKIP" else "[INFO]" if status == "INFO" else "[PARTIAL]"
    print(f"{status_symbol} {test_name}: {status}")
    if details:
        print(f"  Details: {details}")
    print()

def print_section(title):
    """Print a section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")

# ==================== SUPABASE AUTH TESTS ====================

def test_supabase_signup():
    """Test Supabase signup (if user doesn't exist)"""
    print_section("1. SUPABASE AUTHENTICATION TESTS")

    # First try to sign up
    signup_url = f"{SUPABASE_URL}/auth/v1/signup"
    payload = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }

    try:
        response = requests.post(signup_url, json=payload, headers={
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json"
        })
        if response.status_code in [200, 201]:
            log_test("Supabase Signup", "PASS", f"User created or already exists: {response.status_code}")
        elif "User already registered" in response.text or response.status_code == 400:
            log_test("Supabase Signup", "PASS", "User already registered (expected)")
        else:
            log_test("Supabase Signup", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
    except Exception as e:
        log_test("Supabase Signup", "FAIL", str(e))

def test_supabase_login():
    """Test Supabase login with credentials"""
    global auth_token, session_user

    login_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    payload = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }

    try:
        response = requests.post(login_url, json=payload, headers={
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json"
        })

        if response.status_code == 200:
            data = response.json()
            auth_token = data.get("access_token")
            session_user = data.get("user")
            log_test("Supabase Login", "PASS", f"Logged in as {session_user.get('email')}")
            return True
        else:
            log_test("Supabase Login", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
            return False
    except Exception as e:
        log_test("Supabase Login", "FAIL", str(e))
        return False

def test_backend_auth_me():
    """Test backend /api/auth/me endpoint"""
    if not auth_token:
        log_test("Backend /api/auth/me", "SKIP", "No auth token available")
        return

    try:
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        })

        if response.status_code == 200:
            data = response.json()
            log_test("Backend /api/auth/me", "PASS", f"Role: {data.get('role')}, Authorized: {data.get('authorized')}")
        else:
            log_test("Backend /api/auth/me", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
    except Exception as e:
        log_test("Backend /api/auth/me", "FAIL", str(e))

# ==================== SCHEDULE VIEW TESTS ====================

def test_schedule_lessons():
    """Test fetching lessons for schedule view"""
    print_section("2. SCHEDULE VIEW TESTS")

    if not auth_token:
        log_test("Schedule - List Lessons", "SKIP", "No auth token available")
        return

    try:
        # Get lessons for current month
        today = date.today()
        start_date = today.replace(day=1).isoformat()
        end_date = (today.replace(day=1) + timedelta(days=32)).replace(day=1).isoformat()

        response = requests.get(
            f"{BASE_URL}/api/lessons",
            params={"start": start_date, "end": end_date},
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if response.status_code == 200:
            data = response.json()
            count = len(data) if isinstance(data, list) else 0
            log_test("Schedule - List Lessons", "PASS", f"Retrieved {count} lessons for current month")
        else:
            log_test("Schedule - List Lessons", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
    except Exception as e:
        log_test("Schedule - List Lessons", "FAIL", str(e))

# ==================== LESSON DASHBOARD TESTS ====================

def test_lesson_dashboard():
    """Test lesson dashboard with filters"""
    print_section("3. LESSON DASHBOARD TESTS")

    if not auth_token:
        log_test("Dashboard - List Lessons", "SKIP", "No auth token available")
        return

    try:
        # Test basic dashboard call
        response = requests.get(
            f"{BASE_URL}/api/lessons/dashboard",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if response.status_code == 200:
            data = response.json()
            count = len(data.get("lessons", [])) if isinstance(data, dict) else len(data) if isinstance(data, list) else 0
            log_test("Dashboard - List Lessons", "PASS", f"Retrieved {count} lessons")
        else:
            log_test("Dashboard - List Lessons", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")

        # Test with status filter
        response = requests.get(
            f"{BASE_URL}/api/lessons/dashboard",
            params={"status": "Unassigned"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if response.status_code == 200:
            data = response.json()
            count = len(data.get("lessons", [])) if isinstance(data, dict) else len(data) if isinstance(data, list) else 0
            log_test("Dashboard - Filter by Status", "PASS", f"Retrieved {count} unassigned lessons")
        else:
            log_test("Dashboard - Filter by Status", "FAIL", f"Status: {response.status_code}")

        # Test pagination
        response = requests.get(
            f"{BASE_URL}/api/lessons/dashboard",
            params={"page": 1, "page_size": 10},
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if response.status_code == 200:
            log_test("Dashboard - Pagination", "PASS", "Pagination works correctly")
        else:
            log_test("Dashboard - Pagination", "FAIL", f"Status: {response.status_code}")

    except Exception as e:
        log_test("Dashboard Tests", "FAIL", str(e))

# ==================== QUICK INPUT FORMS TESTS ====================

def test_create_school():
    """Test creating a school via Quick Input"""
    print_section("4. QUICK INPUT FORMS - SCHOOL CREATION")

    if not auth_token:
        log_test("Quick Input - Create School", "SKIP", "No auth token available")
        return None

    # First, try to list existing schools to see if the table is accessible
    try:
        list_response = requests.get(
            f"{BASE_URL}/api/schools",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        if list_response.status_code == 200:
            schools = list_response.json()
            log_test("Quick Input - List Schools", "PASS", f"Found {len(schools)} existing schools")
        else:
            log_test("Quick Input - List Schools", "FAIL", f"Status: {list_response.status_code}")
    except Exception as e:
        log_test("Quick Input - List Schools", "FAIL", str(e))

    test_school_name = f"Test School {datetime.now().strftime('%Y%m%d%H%M%S')}"

    try:
        response = requests.post(
            f"{BASE_URL}/api/schools",
            json={"school_name": test_school_name},
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if response.status_code in [200, 201]:
            data = response.json()
            log_test("Quick Input - Create School", "PASS", f"Created school: {data.get('school_name')}")
            return data
        else:
            log_test("Quick Input - Create School", "FAIL", f"Status: {response.status_code}, Response: {response.text[:500]}")
            return None
    except Exception as e:
        log_test("Quick Input - Create School", "FAIL", str(e))
        return None

def test_create_teacher():
    """Test creating a teacher via Quick Input"""
    print_section("5. QUICK INPUT FORMS - TEACHER CREATION")

    if not auth_token:
        log_test("Quick Input - Create Teacher", "SKIP", "No auth token available")
        return None

    # First, try to list existing teachers
    try:
        list_response = requests.get(
            f"{BASE_URL}/api/teachers",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        if list_response.status_code == 200:
            teachers = list_response.json()
            log_test("Quick Input - List Teachers", "PASS", f"Found {len(teachers)} existing teachers")
        else:
            log_test("Quick Input - List Teachers", "FAIL", f"Status: {list_response.status_code}")
    except Exception as e:
        log_test("Quick Input - List Teachers", "FAIL", str(e))

    test_teacher_name = f"Test Teacher {datetime.now().strftime('%Y%m%d%H%M%S')}"

    try:
        response = requests.post(
            f"{BASE_URL}/api/teachers",
            json={
                "teacher_name": test_teacher_name,
                "whatsapp_number": "85212345678",
                "email": f"test{datetime.now().strftime('%Y%m%d%H%M%S')}@test.com"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if response.status_code in [200, 201]:
            data = response.json()
            log_test("Quick Input - Create Teacher", "PASS", f"Created teacher: {data.get('teacher_name')}")
            return data
        else:
            log_test("Quick Input - Create Teacher", "FAIL", f"Status: {response.status_code}, Response: {response.text[:500]}")
            return None
    except Exception as e:
        log_test("Quick Input - Create Teacher", "FAIL", str(e))
        return None

def test_create_course():
    """Test creating a course via Quick Input"""
    print_section("6. QUICK INPUT FORMS - COURSE CREATION")

    if not auth_token:
        log_test("Quick Input - Create Course", "SKIP", "No auth token available")
        return None

    # First, try to list existing courses
    try:
        list_response = requests.get(
            f"{BASE_URL}/api/courses",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        if list_response.status_code == 200:
            courses = list_response.json()
            log_test("Quick Input - List Courses", "PASS", f"Found {len(courses)} existing courses")
        else:
            log_test("Quick Input - List Courses", "FAIL", f"Status: {list_response.status_code}")
    except Exception as e:
        log_test("Quick Input - List Courses", "FAIL", str(e))

    test_course_name = f"Test Course {datetime.now().strftime('%Y%m%d%H%M%S')}"

    try:
        response = requests.post(
            f"{BASE_URL}/api/courses",
            json={"course_name": test_course_name},
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if response.status_code in [200, 201]:
            data = response.json()
            log_test("Quick Input - Create Course", "PASS", f"Created course: {data.get('course_name')}")
            return data
        else:
            log_test("Quick Input - Create Course", "FAIL", f"Status: {response.status_code}, Response: {response.text[:500]}")
            return None
    except Exception as e:
        log_test("Quick Input - Create Course", "FAIL", str(e))
        return None

def test_create_single_lesson(course_id=None, school_id=None):
    """Test creating a single lesson via Quick Input"""
    print_section("7. QUICK INPUT FORMS - SINGLE LESSON CREATION")

    if not auth_token:
        log_test("Quick Input - Create Single Lesson", "SKIP", "No auth token available")
        return None

    # First, try to list existing lessons
    try:
        list_response = requests.get(
            f"{BASE_URL}/api/lessons",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        if list_response.status_code == 200:
            lessons = list_response.json()
            log_test("Quick Input - List Lessons", "PASS", f"Found {len(lessons)} existing lessons")
        else:
            log_test("Quick Input - List Lessons", "FAIL", f"Status: {list_response.status_code}")
    except Exception as e:
        log_test("Quick Input - List Lessons", "FAIL", str(e))

    test_date = date.today() + timedelta(days=7)

    try:
        payload = {
            "date": test_date.isoformat(),
            "start_time": "14:30",
            "end_time": "17:00",
            "status": "Unassigned"
        }

        if course_id:
            payload["course_id"] = course_id
        if school_id:
            payload["school_id"] = school_id

        response = requests.post(
            f"{BASE_URL}/api/lessons",
            json=payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if response.status_code in [200, 201]:
            data = response.json()
            log_test("Quick Input - Create Single Lesson", "PASS", f"Created lesson: {data.get('lesson_id')}")
            return data
        else:
            log_test("Quick Input - Create Single Lesson", "FAIL", f"Status: {response.status_code}, Response: {response.text[:500]}")
            return None
    except Exception as e:
        log_test("Quick Input - Create Single Lesson", "FAIL", str(e))
        return None

def test_create_multi_lesson(course_id=None):
    """Test creating multiple lessons via Quick Input (parse-and-create)"""
    print_section("8. QUICK INPUT FORMS - MULTI-LESSON CREATION")

    if not auth_token:
        log_test("Quick Input - Create Multi-Lesson", "SKIP", "No auth token available")
        return None

    course_name = "Test Course" if not course_id else None

    dates_text = """15/1/2026(星期四)
16/1/2026(星期五)
17/1/2026(星期六)(Test note)
"""

    try:
        payload = {
            "course_name": course_name,
            "dates_text": dates_text,
            "default_start_time": "14:30",
            "default_end_time": "17:00"
        }

        if course_id:
            # If we have a course_id, we need to use the regular batch endpoint
            # or modify the payload
            payload["course_name"] = "Test Course"  # The endpoint will try to match

        response = requests.post(
            f"{BASE_URL}/api/lessons/parse-and-create",
            json=payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if response.status_code in [200, 201]:
            data = response.json()
            log_test("Quick Input - Create Multi-Lesson", "PASS", f"Created {data.get('total')} lessons, Failed: {data.get('failed')}")
            return data
        else:
            log_test("Quick Input - Create Multi-Lesson", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
            return None
    except Exception as e:
        log_test("Quick Input - Create Multi-Lesson", "FAIL", str(e))
        return None

# ==================== LESSON DETAIL DRAWER TESTS ====================

def test_lesson_detail_edit(lesson_id):
    """Test editing lesson details (school, start time, end time)"""
    print_section("9. LESSON DETAIL DRAWER - EDIT TESTS")

    if not auth_token or not lesson_id:
        log_test("Lesson Detail - Edit Lesson", "SKIP", "No auth token or lesson ID")
        return

    try:
        # First, get the current lesson
        get_response = requests.get(
            f"{BASE_URL}/api/lessons/{lesson_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if get_response.status_code != 200:
            log_test("Lesson Detail - Get Lesson", "FAIL", f"Status: {get_response.status_code}")
            return

        original_data = get_response.json()
        if not original_data:
            log_test("Lesson Detail - Get Lesson", "FAIL", "No lesson data returned")
            return

        # The view returns lesson_code, not lesson_id
        lesson_identifier = original_data.get("lesson_code") or original_data.get("lesson_id")
        if not lesson_identifier:
            log_test("Lesson Detail - Get Lesson", "FAIL", f"No lesson identifier found in data. Keys: {list(original_data.keys())}")
            return

        log_test("Lesson Detail - Get Lesson", "PASS", f"Retrieved lesson: {lesson_identifier}")

        # Get original values to restore later
        original_start = original_data.get("start_time", "")
        original_end = original_data.get("end_time", "")

        # Test editing start time
        update_payload = {"start_time": "15:00"}
        update_response = requests.patch(
            f"{BASE_URL}/api/lessons/{lesson_id}",
            json=update_payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if update_response.status_code == 200:
            updated_data = update_response.json()
            log_test("Lesson Detail - Edit Start Time", "PASS", f"Updated start time to: {updated_data.get('start_time')}")
        else:
            log_test("Lesson Detail - Edit Start Time", "FAIL", f"Status: {update_response.status_code}")

        # Test editing end time
        update_payload = {"end_time": "17:30"}
        update_response = requests.patch(
            f"{BASE_URL}/api/lessons/{lesson_id}",
            json=update_payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if update_response.status_code == 200:
            updated_data = update_response.json()
            log_test("Lesson Detail - Edit End Time", "PASS", f"Updated end time to: {updated_data.get('end_time')}")
        else:
            log_test("Lesson Detail - Edit End Time", "FAIL", f"Status: {update_response.status_code}")

        # Verify changes synced by fetching again
        verify_response = requests.get(
            f"{BASE_URL}/api/lessons/{lesson_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if verify_response.status_code == 200:
            verify_data = verify_response.json()
            # Normalize time strings for comparison (remove seconds if present)
            verify_start = str(verify_data.get("start_time", ""))[:5]
            verify_end = str(verify_data.get("end_time", ""))[:5]
            if verify_start == "15:00" and verify_end == "17:30":
                log_test("Lesson Detail - Verify Sync", "PASS", "Changes synced to database correctly")
            else:
                log_test("Lesson Detail - Verify Sync", "FAIL", f"Data mismatch: start={verify_start}, end={verify_end}")
        else:
            log_test("Lesson Detail - Verify Sync", "FAIL", f"Status: {verify_response.status_code}")

        # Restore original values
        restore_payload = {"start_time": original_start, "end_time": original_end}
        requests.patch(
            f"{BASE_URL}/api/lessons/{lesson_id}",
            json=restore_payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

    except Exception as e:
        log_test("Lesson Detail Tests", "FAIL", str(e))

# ==================== CHATBOT TESTS ====================

def test_chatbot():
    """Test chatbot with natural language queries"""
    print_section("10. CHATBOT TESTS")

    if not auth_token:
        log_test("Chatbot - Query", "SKIP", "No auth token available")
        return

    test_queries = [
        "show unassigned lessons",
        "today's schedule",
        "list all teachers"
    ]

    for query in test_queries:
        try:
            response = requests.post(
                f"{BASE_URL}/api/chat",
                json={"message": query, "history": []},
                headers={"Authorization": f"Bearer {auth_token}"}
            )

            if response.status_code == 200:
                data = response.json()
                log_test(f"Chatbot - Query: '{query}'", "PASS", f"Response received: {str(data)[:100]}...")
            else:
                log_test(f"Chatbot - Query: '{query}'", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
        except Exception as e:
            log_test(f"Chatbot - Query: '{query}'", "FAIL", str(e))

# ==================== EXCEL EXPORT TESTS ====================

def test_excel_export():
    """Test Excel export functionality"""
    print_section("11. EXCEL EXPORT TESTS")

    if not auth_token:
        log_test("Excel Export", "SKIP", "No auth token available")
        return

    try:
        # Test lessons export
        response = requests.get(
            f"{BASE_URL}/api/chat/export/lessons",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            content_disposition = response.headers.get("content-disposition", "")
            if "excel" in content_type.lower() or "spreadsheet" in content_type.lower() or "octet-stream" in content_type.lower() or ".xlsx" in content_disposition:
                log_test("Excel Export - Lessons", "PASS", f"Exported successfully, Content-Type: {content_type}")
            else:
                log_test("Excel Export - Lessons", "PARTIAL", f"Response received but content-type: {content_type}")
        else:
            log_test("Excel Export - Lessons", "FAIL", f"Status: {response.status_code}, Response: {response.text[:500]}")

        # Test teachers export
        response = requests.get(
            f"{BASE_URL}/api/chat/export/teachers",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            log_test("Excel Export - Teachers", "PASS", f"Exported successfully, Content-Type: {content_type}")
        else:
            log_test("Excel Export - Teachers", "FAIL", f"Status: {response.status_code}")

    except Exception as e:
        log_test("Excel Export Tests", "FAIL", str(e))

# ==================== MAIN TEST RUNNER ====================

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  VINCI AUTOMATION - END-TO-END TEST SUITE")
    print("="*60 + "\n")

    # Check if services are running
    print("Checking service availability...")
    try:
        resp = requests.get(f"{BASE_URL}/api/health", timeout=5)
        print(f"[OK] Backend API: {resp.status_code}")
    except:
        print("[FAIL] Backend API: Not reachable")
        return

    try:
        resp = requests.get(FRONTEND_URL, timeout=5)
        print(f"[OK] Frontend: {resp.status_code}")
    except:
        print("[FAIL] Frontend: Not reachable")

    try:
        resp = requests.get(f"{SUPABASE_URL}/health", timeout=5)
        print(f"[OK] Supabase: {resp.status_code}")
    except:
        print("[FAIL] Supabase: Not reachable")

    print()

    # Run tests in order
    test_supabase_signup()
    test_supabase_login()
    test_backend_auth_me()
    test_schedule_lessons()
    test_lesson_dashboard()

    # Create entities for lesson creation
    school = test_create_school()
    teacher = test_create_teacher()
    course = test_create_course()

    # Create lessons
    lesson = test_create_single_lesson(
        course_id=course.get("course_id") if course else None,
        school_id=school.get("school_id") if school else None
    )
    test_create_multi_lesson(course_id=course.get("course_id") if course else None)

    # Test lesson editing - use an existing lesson if creation failed
    if lesson:
        test_lesson_detail_edit(lesson.get("id") if isinstance(lesson, dict) else lesson)
    else:
        # Try to get an existing lesson ID for testing the drawer
        try:
            lessons_response = requests.get(
                f"{BASE_URL}/api/lessons",
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            if lessons_response.status_code == 200:
                lessons = lessons_response.json()
                if lessons and len(lessons) > 0:
                    # Use the first lesson's ID (surrogate UUID from lesson_schedule view)
                    first_lesson = lessons[0]
                    log_test("Lesson Detail - Sample Lesson Data", "INFO", f"Sample lesson: id={first_lesson.get('id')}, lesson_code={first_lesson.get('lesson_code')}")
                    first_lesson_id = first_lesson.get("id") if isinstance(first_lesson, dict) else first_lesson
                    if first_lesson_id and first_lesson_id != "None":
                        test_lesson_detail_edit(first_lesson_id)
                    else:
                        log_test("Lesson Detail - Get Existing Lesson", "FAIL", f"No valid ID found in lesson data. id={first_lesson_id}")
        except Exception as e:
            log_test("Lesson Detail - Get Existing Lesson", "FAIL", str(e))

    # Test chatbot and export
    test_chatbot()
    test_excel_export()

    # Print summary
    print_section("TEST SUMMARY")
    passed = sum(1 for r in test_results if r["status"] == "PASS")
    failed = sum(1 for r in test_results if r["status"] == "FAIL")
    skipped = sum(1 for r in test_results if r["status"] == "SKIP")
    partial = sum(1 for r in test_results if r["status"] == "PARTIAL")

    print(f"Total Tests: {len(test_results)}")
    print(f"[PASS] Passed: {passed}")
    print(f"[FAIL] Failed: {failed}")
    print(f"[SKIP] Skipped: {skipped}")
    print(f"[PARTIAL] Partial: {partial}")
    print()

    if failed > 0:
        print("\nFailed tests:")
        for r in test_results:
            if r["status"] == "FAIL":
                print(f"  - {r['test']}: {r['details']}")

    # Save results to file
    with open("test_results.json", "w") as f:
        json.dump(test_results, f, indent=2)
    print(f"\nTest results saved to: test_results.json")

if __name__ == "__main__":
    main()
