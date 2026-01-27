"""Offer catalog routes using SQLAlchemy."""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import OfferCatalogModel
from models.offers_catalog import OfferCatalog, OfferCatalogListResponse, STAGE_ACTIONS


router = APIRouter(prefix="/v3", tags=["Offers"])


def _split_csv(value):
    if value is None:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


def _to_offer_catalog(model: OfferCatalogModel) -> OfferCatalog:
    """Convert SQLAlchemy model to Pydantic."""
    data = {c.name: getattr(model, c.name) for c in model.__table__.columns}
    data["eligible_sports"] = _split_csv(data.get("eligible_sports"))
    data["eligible_markets"] = _split_csv(data.get("eligible_markets"))
    return OfferCatalog.model_validate(data)


@router.get("/offers", response_model=OfferCatalogListResponse)
def list_offers(
    limit: int = Query(200, le=200),
    offer_type: Optional[str] = None,
    bookmaker: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List offers from catalog with basic filters."""
    stmt = select(OfferCatalogModel)

    if offer_type:
        stmt = stmt.where(OfferCatalogModel.offer_type == offer_type)
    if bookmaker:
        stmt = stmt.where(OfferCatalogModel.bookmaker == bookmaker)

    stmt = stmt.where(OfferCatalogModel.is_active.is_(True)).limit(limit)
    rows = db.execute(stmt).scalars().all()

    offers = [_to_offer_catalog(row) for row in rows]
    return OfferCatalogListResponse(offers=offers, total=len(offers))


@router.get("/offers/{offer_id}", response_model=OfferCatalog)
def get_offer(offer_id: str, db: Session = Depends(get_db)):
    """Fetch a single offer by ID."""
    stmt = select(OfferCatalogModel).where(OfferCatalogModel.id == offer_id)
    row = db.execute(stmt).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Offer not found")
    return _to_offer_catalog(row)


@router.get("/offers/stages/actions")
def get_stage_actions():
    """Get the action text for each offer stage."""
    return STAGE_ACTIONS

