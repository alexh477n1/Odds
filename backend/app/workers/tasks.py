"""Background tasks for scraping and recalculation."""
import asyncio
from celery.utils.log import get_task_logger
from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.services import offers as offers_service


logger = get_task_logger(__name__)


@celery_app.task(name="tasks.scrape_offers")
def scrape_offers_task():
    """Run the odds scraper and update offers."""
    logger.info("Starting scrape_offers_task")
    with SessionLocal() as db:
        result = offers_service.update_offers_from_scraper(db)
    logger.info("Scrape completed: %s", result)
    return result


@celery_app.task(name="tasks.seed_offers")
def seed_offers_task(force: bool = False):
    """Seed the offers catalog."""
    logger.info("Starting seed_offers_task (force=%s)", force)
    with SessionLocal() as db:
        if force:
            offers_service.clear_offers(db)
        created = offers_service.seed_sample_offers(db)
    return {"seeded": True, "force": force, "created": created}

