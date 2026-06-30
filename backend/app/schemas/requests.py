"""Pydantic request models for the REST API.

Field names match the Airtable-mirroring columns. Times are accepted as
"HH:MM" strings; dates as ISO "YYYY-MM-DD". Update models make every field
optional so PATCH can send partial bodies.
"""

from __future__ import annotations

from datetime import date as date_t

from pydantic import BaseModel


# --- Schools (PK: school_id — generated when omitted) ---------------------
class SchoolCreate(BaseModel):
    school_id: str | None = None
    school_name: str | None = None
    tutor_availability_submissions: str | None = None
    tutor_availability_slots: str | None = None


class SchoolUpdate(BaseModel):
    school_name: str | None = None
    tutor_availability_submissions: str | None = None
    tutor_availability_slots: str | None = None


# --- Teachers (PK: teacher_id — generated when omitted) -------------------
class TeacherCreate(BaseModel):
    teacher_id: str | None = None
    teacher_name: str | None = None
    email: str | None = None
    whatsapp_number: str | None = None
    status: str = "Active"
    tutor_rate: float | None = None
    ta_rate: float | None = None
    reliability_score: float | None = None
    background: str | None = None
    cv_link: str | None = None


class TeacherUpdate(BaseModel):
    teacher_name: str | None = None
    email: str | None = None
    whatsapp_number: str | None = None
    status: str | None = None
    tutor_rate: float | None = None
    ta_rate: float | None = None
    reliability_score: float | None = None
    background: str | None = None
    cv_link: str | None = None


# --- Courses (PK: course_id — generated from the name when omitted) -------
class CourseCreate(BaseModel):
    course_id: str | None = None
    course_name: str | None = None
    school_id: str | None = None
    course_topic: str | None = None
    course_types: str | None = None
    revenue_per_lesson: float | None = None


class CourseUpdate(BaseModel):
    course_name: str | None = None
    school_id: str | None = None
    course_topic: str | None = None
    course_types: str | None = None
    revenue_per_lesson: float | None = None


# --- Lessons (surrogate id; teacher_id / course_id FKs) -------------------
class LessonCreate(BaseModel):
    date: date_t
    lesson_id: str | None = None
    course_id: str | None = None
    teacher_id: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    status: str | None = "Scheduled"
    role: str | None = None
    tutor_assignment: str | None = None
    lesson_material_link: str | None = None
    max_tutors: int = 1
    lesson_income: float | None = None
    notes: str | None = None


class LessonUpdate(BaseModel):
    date: date_t | None = None
    lesson_id: str | None = None
    course_id: str | None = None
    teacher_id: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    status: str | None = None
    role: str | None = None
    tutor_assignment: str | None = None
    lesson_material_link: str | None = None
    max_tutors: int | None = None
    lesson_income: float | None = None
    notes: str | None = None


# --- Scheduling actions ----------------------------------------------------
class AssignRequest(BaseModel):
    teacher_id: str
    send_files: bool = True


class AnnounceLessonRequest(BaseModel):
    """Create a lesson and message the tutors the LLM judges suitable."""
    date: date_t
    lesson_code: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    course: str | None = None   # course name (resolved to a course_id if it matches one)
    school: str | None = None   # school name (context for matching + the WhatsApp message)
    max_tutors: int = 1         # max tutors that can be assigned to this lesson
    lesson_income: float | None = None


# --- Chatbot ---------------------------------------------------------------
class ChatMessage(BaseModel):
    role: str = "user"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
