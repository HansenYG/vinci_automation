from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.core.database import get_supabase
from app.schemas.requests import CourseCreate, CourseUpdate
from app.services import codes, repos

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("")
def list_courses(db: Client = Depends(get_supabase)):
    return repos.list_rows(db, "courses", order="course_name")


@router.post("", status_code=201)
def create_course(body: CourseCreate, db: Client = Depends(get_supabase)):
    payload = body.model_dump(exclude_none=True)
    payload.setdefault("course_id", codes.next_course_id(db, payload.get("course_name")))
    return repos.insert_row(db, "courses", payload)


@router.get("/{course_id}")
def get_course(course_id: str, db: Client = Depends(get_supabase)):
    row = repos.get_row(db, "courses", course_id)
    if not row:
        raise HTTPException(404, "course not found")
    return row


@router.patch("/{course_id}")
def update_course(course_id: str, body: CourseUpdate, db: Client = Depends(get_supabase)):
    row = repos.update_row(db, "courses", course_id, body.model_dump(exclude_none=True))
    if not row:
        raise HTTPException(404, "course not found")
    return row


@router.delete("/{course_id}", status_code=204)
def delete_course(course_id: str, db: Client = Depends(get_supabase)):
    repos.delete_row(db, "courses", course_id)
