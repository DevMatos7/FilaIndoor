"""Retail sync scheduler — single APScheduler engine, store-scoped jobs."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.retail.models import RetailStoreSource
from app.modules.retail.provider_guard import assert_retail_provider_safe, provider_label, retail_provider_is_mock
from app.modules.retail.sync_service import ENTITIES, RetailSyncService

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_started_at: datetime | None = None
_last_tick: dict[str, str] = {}


def _entity_seconds(entity: str) -> int:
    s = get_settings()
    return {
        "PRODUCT": s.retail_sync_product_seconds,
        "PRICE": s.retail_sync_price_seconds,
        "PROMOTION": s.retail_sync_promotion_seconds,
        "AVAILABILITY": s.retail_sync_availability_seconds,
        "OFFER": s.retail_sync_offer_seconds,
        "PRODUCT_IMAGE": s.retail_sync_product_image_seconds,
        "PRICE_CHAIN": s.retail_sync_price_chain_seconds,
    }.get(entity, 300)


def _run_scheduled(entity: str) -> None:
    settings = get_settings()
    if not settings.retail_automation_enabled:
        return
    try:
        assert_retail_provider_safe(for_automation=True)
    except Exception as exc:  # noqa: BLE001
        logger.error("retail.sync.scheduled_aborted entity=%s err=%s", entity, exc)
        return

    db = SessionLocal()
    try:
        sources = list(
            db.scalars(
                select(RetailStoreSource).where(
                    RetailStoreSource.active.is_(True),
                    RetailStoreSource.source_system == "CISS",
                )
            ).all()
        )
        logger.info("retail.sync.scheduled entity=%s stores=%s", entity, len(sources))
        for src in sources:
            try:
                logger.info("retail.sync.started store=%s entity=%s trigger=SCHEDULED", src.store_id, entity)
                RetailSyncService(db).sync_store(
                    src.store_id, entities=[entity], full=False, trigger="SCHEDULED"
                )
                _last_tick[f"{src.store_id}:{entity}"] = datetime.now(timezone.utc).isoformat()
                logger.info("retail.sync.completed store=%s entity=%s", src.store_id, entity)
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "retail.sync.failed store=%s entity=%s err=%s", src.store_id, entity, exc
                )
    finally:
        db.close()


def start_retail_scheduler() -> BackgroundScheduler | None:
    global _scheduler, _started_at
    settings = get_settings()
    if _scheduler and _scheduler.running:
        return _scheduler
    if not settings.retail_automation_enabled:
        logger.info("retail.scheduler.disabled")
        return None
    if settings.is_production and retail_provider_is_mock(settings) and not settings.retail_allow_mock_in_production:
        logger.error("retail.scheduler.not_started production_mock_rejected")
        return None

    sched = BackgroundScheduler(timezone="UTC")
    for entity in ENTITIES:
        seconds = max(15, int(_entity_seconds(entity)))
        sched.add_job(
            _run_scheduled,
            trigger=IntervalTrigger(seconds=seconds),
            args=[entity],
            id=f"retail-sync-{entity.lower()}",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
    sched.start()
    _scheduler = sched
    _started_at = datetime.now(timezone.utc)
    logger.info(
        "retail.scheduler.started provider=%s intervals=%s",
        provider_label(settings),
        {e: _entity_seconds(e) for e in ENTITIES},
    )
    return sched


def shutdown_retail_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("retail.scheduler.stopped")
    _scheduler = None


def scheduler_status() -> dict[str, Any]:
    settings = get_settings()
    jobs = []
    if _scheduler:
        for job in _scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "next_run_at": job.next_run_time.isoformat() if job.next_run_time else None,
                }
            )
    return {
        "enabled": bool(settings.retail_automation_enabled),
        "running": bool(_scheduler and _scheduler.running),
        "provider": provider_label(settings),
        "provider_raw": settings.retail_provider,
        "is_production": settings.is_production,
        "started_at": _started_at.isoformat() if _started_at else None,
        "intervals_seconds": {e: _entity_seconds(e) for e in ENTITIES},
        "jobs": jobs,
        "last_ticks": dict(_last_tick),
        "freshness": {
            "warn_after_seconds": settings.retail_warn_after_seconds,
            "hard_stop_after_seconds": settings.retail_hard_stop_after_seconds,
        },
    }
