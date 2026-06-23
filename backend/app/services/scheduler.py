"""Optional in-process scheduler (APScheduler).

Disabled by default (ENABLE_SCHEDULER=false). On Render's free web tier the
service sleeps, so a Cron Job hitting /api/scheduling/run-due-reminders is more
reliable; flip this on only for an always-on worker.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.database import get_supabase
from app.services import scheduling

logger = logging.getLogger("vinci.scheduler")


def _tick() -> None:
    try:
        summary = scheduling.run_due_reminders(get_supabase())
        logger.info("reminder sweep: %s", summary)
    except Exception:  # noqa: BLE001 - never let a tick kill the scheduler
        logger.exception("reminder sweep failed")


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        _tick,
        "interval",
        minutes=settings.SCHEDULER_TICK_MINUTES,
        id="reminder_sweep",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("in-process scheduler started (every %s min)", settings.SCHEDULER_TICK_MINUTES)
    return scheduler
