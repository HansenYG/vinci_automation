from fastapi import APIRouter, Depends, HTTPException
from postgrest import SyncPostgrestClient

from app.api.deps import get_db
from app.schemas.requests import SchoolCreate, SchoolUpdate
from app.services import codes, repos

router = APIRouter(prefix="/schools", tags=["schools"])


@router.get("")
def list_schools(db: SyncPostgrestClient = Depends(get_db)):
    return repos.list_rows(db, "schools", order="school_name")


@router.post("", status_code=201)
def create_school(body: SchoolCreate, db: SyncPostgrestClient = Depends(get_db)):
    payload = body.model_dump(exclude_none=True)
    payload.setdefault("school_id", codes.next_school_id(db))
    return repos.insert_row(db, "schools", payload)


@router.get("/{school_id}")
def get_school(school_id: str, db: SyncPostgrestClient = Depends(get_db)):
    row = repos.get_row(db, "schools", school_id)
    if not row:
        raise HTTPException(404, "school not found")
    return row


@router.patch("/{school_id}")
def update_school(school_id: str, body: SchoolUpdate, db: SyncPostgrestClient = Depends(get_db)):
    row = repos.update_row(db, "schools", school_id, body.model_dump(exclude_none=True))
    if not row:
        raise HTTPException(404, "school not found")
    return row


@router.delete("/{school_id}", status_code=204)
def delete_school(school_id: str, db: SyncPostgrestClient = Depends(get_db)):
    repos.delete_row(db, "schools", school_id)
