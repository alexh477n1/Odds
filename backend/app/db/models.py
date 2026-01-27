"""SQLAlchemy models mapping Supabase tables."""
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)
from app.db.base import Base


class OfferCatalogModel(Base):
    """Represents offers_catalog table."""

    __tablename__ = "offers_catalog"

    id = Column(String, primary_key=True, index=True)
    bookmaker = Column(String, nullable=False)
    offer_name = Column(String, nullable=False)
    offer_type = Column(String, nullable=True)
    offer_value = Column(Float, nullable=True)
    required_stake = Column(Float, nullable=True)
    min_odds = Column(Float, nullable=True)
    max_stake = Column(Float, nullable=True)
    wagering_requirement = Column(Float, nullable=True)
    is_stake_returned = Column(Boolean, nullable=True, default=False)
    qualifying_bet_required = Column(Boolean, nullable=True, default=True)
    terms_raw = Column(Text, nullable=True)
    terms_summary = Column(Text, nullable=True)
    expiry_days = Column(Integer, nullable=True)
    eligible_sports = Column(Text, nullable=True)
    eligible_markets = Column(Text, nullable=True)
    signup_url = Column(Text, nullable=True)
    referral_url = Column(Text, nullable=True)
    oddschecker_url = Column(Text, nullable=True)
    difficulty = Column(String, nullable=True)
    expected_profit = Column(Float, nullable=True)
    estimated_time_minutes = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=True, default=True)
    priority_rank = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)


class UserOfferProgressModel(Base):
    """Represents user_offer_progress table."""

    __tablename__ = "user_offer_progress"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    offer_id = Column(String, index=True, nullable=False)
    stage = Column(String, nullable=True)
    qualifying_bet_id = Column(String, nullable=True)
    qualifying_stake = Column(Float, nullable=True)
    qualifying_odds = Column(Float, nullable=True)
    qualifying_loss = Column(Float, nullable=True)
    free_bet_id = Column(String, nullable=True)
    free_bet_value = Column(Float, nullable=True)
    free_bet_profit = Column(Float, nullable=True)
    total_profit = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    signed_up_at = Column(DateTime, nullable=True)
    qualifying_placed_at = Column(DateTime, nullable=True)
    free_bet_received_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

