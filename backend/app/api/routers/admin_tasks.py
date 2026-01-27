"""Admin endpoints for background tasks."""
from fastapi import APIRouter, Depends
from app.api.deps import require_admin
from app.workers.tasks import scrape_offers_task, seed_offers_task


router = APIRouter(prefix="/admin/tasks", tags=["Admin"])


@router.post("/scrape")
def trigger_scrape(_: dict = Depends(require_admin)):
    """Trigger offers scraping in the background."""
    task = scrape_offers_task.delay()
    return {"task_id": task.id, "status": "queued"}


@router.post("/seed")
def trigger_seed(force: bool = False, _: dict = Depends(require_admin)):
    """Trigger seeding sample offers."""
    task = seed_offers_task.delay(force=force)
    return {"task_id": task.id, "status": "queued", "force": force}

