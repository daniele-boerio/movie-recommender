"""Scheduler in-app (APScheduler) per i controlli periodici.

Gira dentro il processo uvicorn: nessuna infra separata. Con un'unica replica/worker
(il nostro caso) c'è una sola istanza dello scheduler, quindi niente esecuzioni doppie.
"""

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .database import SessionLocal
from .services.notifier import scan_new_episodes
from .tmdb import tmdb_get

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler(timezone="UTC")


async def _episodes_job() -> None:
    db = SessionLocal()
    try:
        n = await scan_new_episodes(db, tmdb_get)
        if n:
            logger.info("Notifiche nuovi episodi create: %d", n)
    except Exception as e:  # un errore nel job non deve buttare giù nulla
        logger.error("Errore nel job notifiche: %s", e)
    finally:
        db.close()


def start_scheduler() -> None:
    # Ogni 6 ore, con una prima passata poco dopo l'avvio.
    _scheduler.add_job(
        _episodes_job,
        "interval",
        hours=6,
        next_run_time=datetime.now(timezone.utc) + timedelta(minutes=2),
        id="new_episodes",
        max_instances=1,
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler avviato (controllo nuovi episodi ogni 6h).")


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
