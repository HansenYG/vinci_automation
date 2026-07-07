from fastapi import APIRouter, Depends, HTTPException
from postgrest import SyncPostgrestClient

from app.api.deps import get_db
from app.schemas.requests import CourseCreate, CourseUpdate
from app.services import codes, repos

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("")
def list_courses(db: SyncPostgrestClient = Depends(get_db)):
    return repos.list_rows(db, "courses", order="course_name")


@router.post("", status_code=201)
def create_course(body: CourseCreate, db: SyncPostgrestClient = Depends(get_db)):
    payload = body.model_dump(exclude_none=True)
    payload.setdefault("course_id", codes.next_course_id(db, payload.get("course_name")))
    return repos.insert_row(db, "courses", payload)


@router.get("/{course_id}")
def get_course(course_id: str, db: SyncPostgrestClient = Depends(get_db)):
    row = repos.get_row(db, "courses", course_id)
    if not row:
        raise HTTPException(404, "course not found")
    return row


@router.patch("/{course_id}")
def update_course(course_id: str, body: CourseUpdate, db: SyncPostgrestClient = Depends(get_db)):
    row = repos.update_row(db, "courses", course_id, body.model_dump(exclude_none=True))
    if not row:
        raise HTTPException(404, "course not found")
    return row


@router.delete("/{course_id}", status_code=204)
def delete_course(course_id: str, db: SyncPostgrestClient = Depends(get_db)):
    repos.delete_row(db, "courses", course_id)
