from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.core.database import get_supabase
from app.schemas.requests import TeacherCreate, TeacherUpdate
from app.services import codes, repos

router = APIRouter(prefix="/teachers", tags=["teachers"])


@router.get("")
def list_teachers(db: Client = Depends(get_supabase)):
    return repos.list_rows(db, "teachers", order="teacher_name")


@router.post("", status_code=201)
def create_teacher(body: TeacherCreate, db: Client = Depends(get_supabase)):
    payload = body.model_dump(exclude_none=True)
    payload.setdefault("teacher_id", codes.next_teacher_id(db))
    return repos.insert_row(db, "teachers", payload)


@router.get("/{teacher_id}")
def get_teacher(teacher_id: str, db: Client = Depends(get_supabase)):
    row = repos.get_row(db, "teachers", teacher_id)
    if not row:
        raise HTTPException(404, "teacher not found")
    return row


@router.patch("/{teacher_id}")
def update_teacher(teacher_id: str, body: TeacherUpdate, db: Client = Depends(get_supabase)):
    row = repos.update_row(db, "teachers", teacher_id, body.model_dump(exclude_none=True))
    if not row:
        raise HTTPException(404, "teacher not found")
    return row


@router.delete("/{teacher_id}", status_code=204)
def delete_teacher(teacher_id: str, db: Client = Depends(get_supabase)):
    repos.delete_row(db, "teachers", teacher_id)
