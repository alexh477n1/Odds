"""Offer catalog services using SQLAlchemy."""
from __future__ import annotations

from datetime import datetime
from typing import List
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from app.db.models import OfferCatalogModel
from models.offers_catalog import OfferCatalogCreate
import asyncio
from scraper.oddschecker_scraper import scrape_oddschecker_offers


def list_offers(db: Session, limit: int = 200) -> List[OfferCatalogModel]:
    stmt = select(OfferCatalogModel).where(OfferCatalogModel.is_active.is_(True)).limit(limit)
    return db.execute(stmt).scalars().all()


def get_offer(db: Session, offer_id: str) -> OfferCatalogModel | None:
    stmt = select(OfferCatalogModel).where(OfferCatalogModel.id == offer_id)
    return db.execute(stmt).scalars().first()


def seed_sample_offers(db: Session) -> int:
    """Seed a minimal set of sample offers for testing."""
    sample_offers = [
        OfferCatalogCreate(
            bookmaker="Bet365",
            offer_name="Bet £10 Get £30 in Free Bets",
            offer_type="welcome",
            offer_value=30.0,
            required_stake=10.0,
            min_odds=1.2,
            terms_summary="Place £10+ at odds 1.20+. Get 3x £10 free bets.",
            expected_profit=22.0,
        ),
        OfferCatalogCreate(
            bookmaker="Sky Bet",
            offer_name="Bet £10 Get £40 in Free Bets",
            offer_type="welcome",
            offer_value=40.0,
            required_stake=10.0,
            min_odds=1.5,
            terms_summary="Bet £10+ at 1.50+. Get £40 in free bets.",
            expected_profit=29.0,
        ),
        OfferCatalogCreate(
            bookmaker="Coral",
            offer_name="Bet £5 Get £20 in Free Bets",
            offer_type="welcome",
            offer_value=20.0,
            required_stake=5.0,
            min_odds=1.5,
            terms_summary="Bet £5+ at 1.50+. Get 4x £5 free bets.",
            expected_profit=14.5,
        ),
    ]

    created = 0
    for offer in sample_offers:
        model = OfferCatalogModel(
            id=str(uuid.uuid4()),
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            **offer.model_dump(exclude_none=True),
        )
        db.add(model)
        created += 1
    db.commit()
    return created


def clear_offers(db: Session) -> int:
    result = db.execute(delete(OfferCatalogModel))
    db.commit()
    return result.rowcount or 0


def update_offers_from_scraper(db: Session) -> dict:
    """Scrape Oddschecker and upsert offers with signup URLs."""
    scraped = asyncio.run(scrape_oddschecker_offers())
    created = 0
    updated = 0

    for offer in scraped:
        bookmaker = offer.get("bookmaker")
        offer_name = offer.get("offer_name")
        if not bookmaker or not offer_name:
            continue

        existing = db.execute(
            select(OfferCatalogModel).where(
                OfferCatalogModel.bookmaker == bookmaker,
                OfferCatalogModel.offer_name == offer_name,
            )
        ).scalars().first()

        if existing:
            existing.signup_url = offer.get("signup_url")
            existing.offer_value = offer.get("offer_value")
            existing.required_stake = offer.get("required_stake")
            existing.min_odds = offer.get("min_odds")
            existing.terms_summary = offer.get("terms_summary")
            existing.updated_at = datetime.utcnow()
            updated += 1
        else:
            model = OfferCatalogModel(
                id=str(uuid.uuid4()),
                bookmaker=bookmaker,
                offer_name=offer_name,
                offer_type="welcome",
                offer_value=offer.get("offer_value"),
                required_stake=offer.get("required_stake"),
                min_odds=offer.get("min_odds"),
                terms_summary=offer.get("terms_summary"),
                signup_url=offer.get("signup_url"),
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(model)
            created += 1

    db.commit()
    return {"scraped_count": len(scraped), "created_count": created, "updated_count": updated}

