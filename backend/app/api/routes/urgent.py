"""Urgent News feed (design Phase 4). Already usable: surfaces lessons within
a week that are unassigned or cancelled, from the urgent_news view."""

from fastapi import APIRouter, Depends
from supabase import Client

from app.core.database import get_supabase

router = APIRouter(prefix="/urgent-news", tags=["urgent-news"])


@router.get("")
def urgent_news(db: Client = Depends(get_supabase)):
    return db.table("urgent_news").select("*").execute().data or []
