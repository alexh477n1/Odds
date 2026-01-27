"""Calculator endpoints."""
from fastapi import APIRouter, HTTPException, Query
from models.calculator import (
    CalcRequest,
    CalcResponse,
    BatchCalcRequest,
    BatchCalcResponse,
)
from utils.calculator import calculate, calculate_batch, calculate_retention_rate


router = APIRouter(tags=["Calculator"])


@router.post("/calculate", response_model=CalcResponse)
def calculate_matched_bet(request: CalcRequest):
    """Calculate matched betting stakes and profits."""
    try:
        return calculate(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/calculate/batch", response_model=BatchCalcResponse)
def calculate_batch_bets(request: BatchCalcRequest):
    """Calculate multiple bets in a single request."""
    try:
        return calculate_batch(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/calculate/retention")
def calculate_free_bet_retention(
    free_bet_value: float = Query(..., description="Value of the free bet"),
    back_odds: float = Query(..., description="Back odds at bookmaker"),
    lay_odds: float = Query(..., description="Lay odds at exchange"),
    commission: float = Query(0.05, description="Exchange commission"),
):
    """Calculate free bet retention rate."""
    try:
        retention = calculate_retention_rate(free_bet_value, back_odds, lay_odds, commission)
        profit = (retention / 100) * free_bet_value
        return {
            "free_bet_value": free_bet_value,
            "back_odds": back_odds,
            "lay_odds": lay_odds,
            "commission": commission,
            "retention_percent": round(retention, 1),
            "guaranteed_profit": round(profit, 2),
            "rating": (
                "Excellent" if retention >= 75 else
                "Good" if retention >= 70 else
                "Fair" if retention >= 60 else
                "Poor"
            ),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

