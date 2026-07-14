"""Chatbot endpoints — query the DB in natural language, export to Excel,
and one-click preset operations."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from postgrest import SyncPostgrestClient

from app.api.deps import get_db
from app.schemas.requests import ChatRequest
from app.services import chatbot, export, repos

router = APIRouter(prefix="/chat", tags=["chat"])


class ExecuteRequest(BaseModel):
    operation: str
    params: dict = {}

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/presets")
def presets():
    return chatbot.PRESETS


@router.post("")
def chat(body: ChatRequest, db: SyncPostgrestClient = Depends(get_db)):
    history = [m.model_dump() for m in body.history]
    return chatbot.answer(db, body.message, history,
                          resolved_school_id=body.resolved_school_id,
                          resolved_course_id=body.resolved_course_id)


@router.post("/execute")
def execute_action(body: ExecuteRequest, db: SyncPostgrestClient = Depends(get_db)):
    return chatbot.execute_operation(db, body.operation, body.params)


@router.get("/export/{dataset}")
def export_dataset(dataset: str, db: SyncPostgrestClient = Depends(get_db)):
    fetchers = {
        "lessons": lambda: db.table("lessons_full").select("*").execute().data or [],
        "unassigned": lambda: repos.list_unassigned(db, 1000),
        "urgent": lambda: db.table("urgent_news").select("*").execute().data or [],
        "teachers": lambda: db.table("teachers_full").select("*").execute().data or [],
        "courses": lambda: db.table("courses_full").select("*").execute().data or [],
        "schools": lambda: db.table("schools_full").select("*").execute().data or [],
    }
    if dataset not in fetchers:
        raise HTTPException(400, f"unknown dataset '{dataset}'")

    data = export.rows_to_xlsx(fetchers[dataset](), sheet_name=dataset)
    headers = {"Content-Disposition": f'attachment; filename="vinci_{dataset}.xlsx"'}
    return StreamingResponse(iter([data]), media_type=_XLSX, headers=headers)
