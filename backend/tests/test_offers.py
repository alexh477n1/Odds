from datetime import datetime, timezone

from app.db.models import OfferCatalogModel


def _insert_offer(session, **overrides):
    offer = OfferCatalogModel(
        id=overrides.get("id", "offer-1"),
        bookmaker=overrides.get("bookmaker", "Bet365"),
        offer_name=overrides.get("offer_name", "Welcome Bonus"),
        offer_type=overrides.get("offer_type", "welcome"),
        offer_value=overrides.get("offer_value", 50.0),
        required_stake=overrides.get("required_stake", 10.0),
        min_odds=overrides.get("min_odds", 1.5),
        max_stake=overrides.get("max_stake", 50.0),
        wagering_requirement=overrides.get("wagering_requirement", 1.0),
        is_stake_returned=overrides.get("is_stake_returned", False),
        qualifying_bet_required=overrides.get("qualifying_bet_required", True),
        terms_raw=overrides.get("terms_raw", "T&Cs apply"),
        terms_summary=overrides.get("terms_summary", "Short summary"),
        expiry_days=overrides.get("expiry_days", 30),
        eligible_sports=overrides.get("eligible_sports", "football,tennis"),
        eligible_markets=overrides.get("eligible_markets", "match-winner"),
        signup_url=overrides.get("signup_url", "https://example.com/signup"),
        referral_url=overrides.get("referral_url", "https://example.com/ref"),
        oddschecker_url=overrides.get("oddschecker_url", "https://example.com/odds"),
        difficulty=overrides.get("difficulty", "easy"),
        expected_profit=overrides.get("expected_profit", 12.5),
        estimated_time_minutes=overrides.get("estimated_time_minutes", 15),
        is_active=overrides.get("is_active", True),
        priority_rank=overrides.get("priority_rank", 1),
        created_at=overrides.get("created_at", datetime.now(timezone.utc)),
        updated_at=overrides.get("updated_at", datetime.now(timezone.utc)),
    )
    session.add(offer)
    session.commit()
    return offer


def test_list_offers_returns_active_only(client, db_session):
    _insert_offer(db_session, id="offer-1", is_active=True)
    _insert_offer(db_session, id="offer-2", is_active=False)

    response = client.get("/v3/offers")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["offers"][0]["id"] == "offer-1"


def test_list_offers_filters_by_type_and_bookmaker(client, db_session):
    _insert_offer(db_session, id="offer-1", offer_type="welcome", bookmaker="Bet365")
    _insert_offer(db_session, id="offer-2", offer_type="reload", bookmaker="SkyBet")

    response = client.get("/v3/offers", params={"offer_type": "reload", "bookmaker": "SkyBet"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["offers"][0]["id"] == "offer-2"


def test_get_offer_returns_404_when_missing(client):
    response = client.get("/v3/offers/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Offer not found"


def test_stage_actions_endpoint(client):
    response = client.get("/v3/offers/stages/actions")

    assert response.status_code == 200
    payload = response.json()
    assert payload["discovered"] == "Start This Offer"
