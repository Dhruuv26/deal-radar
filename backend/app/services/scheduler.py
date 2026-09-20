"""
REQ-P2-1: refresh every tracked listing on a fixed interval (default 6h).

Started from main.py's startup event. A manual trigger also exists at
POST /api/ingestion/refresh-now for demos, since waiting for the real
schedule isn't practical to show live.
"""
from apscheduler.schedulers.background import BackgroundScheduler
import logging

from ..database import SessionLocal
from . import refresh as refresh_service

logger = logging.getLogger("deal_radar.scheduler")

REFRESH_INTERVAL_HOURS = 6

_scheduler = BackgroundScheduler()


def _scheduled_refresh_job():
    db = SessionLocal()
    try:
        results = refresh_service.refresh_all_listings(db)
        logger.info("Scheduled refresh completed for %d listing(s).", len(results))
    finally:
        db.close()


def start_scheduler():
    if not _scheduler.running:
        _scheduler.add_job(
            _scheduled_refresh_job,
            "interval",
            hours=REFRESH_INTERVAL_HOURS,
            id="refresh_all_listings",
            replace_existing=True,
        )
        _scheduler.start()


def stop_scheduler():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
