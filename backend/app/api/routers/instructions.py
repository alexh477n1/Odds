"""Instruction generator endpoints."""
from fastapi import APIRouter, HTTPException
from models.instruction import (
    InstructionRequest,
    InstructionResponse,
    FullOfferInstructionRequest,
    FullOfferInstructionResponse,
)
from utils.instructions import generate_instructions, generate_full_offer_instructions


router = APIRouter(tags=["Instructions"])


@router.post("/generate-instructions", response_model=InstructionResponse)
def generate_betting_instructions(request: InstructionRequest):
    """Generate step-by-step betting instructions."""
    try:
        return generate_instructions(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/generate-instructions/full-offer", response_model=FullOfferInstructionResponse)
def generate_full_offer_betting_instructions(request: FullOfferInstructionRequest):
    """Generate full offer instructions (qualifying + free bet)."""
    try:
        return generate_full_offer_instructions(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

