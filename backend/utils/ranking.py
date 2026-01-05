"""Ranking logic for offers based on Value Index."""
from typing import List, Optional
from backend.models.offer import OfferParsed, OfferRanked


def calculate_value_index(offer: OfferParsed) -> float:
    """
    Calculate the Value Index for an offer.
    
    Formula: offer_value / required_stake
    
    Args:
        offer: Parsed offer object
        
    Returns:
        Value index as float, or 0.0 if cannot be calculated
    """
    if offer.offer_value is None or offer.required_stake is None:
        return 0.0
    
    if offer.required_stake == 0:
        return 0.0
    
    return round(offer.offer_value / offer.required_stake, 4)


def rank_offers(offers: List[OfferParsed], raw_texts: Optional[List[str]] = None) -> List[OfferRanked]:
    """
    Rank offers by Value Index (descending).
    
    Args:
        offers: List of parsed offers
        raw_texts: Optional list of raw texts corresponding to offers (same order)
        
    Returns:
        List of ranked offers sorted by value_index (highest first)
    """
    # Calculate value index for each offer
    ranked_offers = []
    
    for idx, offer in enumerate(offers):
        value_index = calculate_value_index(offer)
        
        ranked_offer = OfferRanked(
            **offer.model_dump(),
            value_index=value_index,
            rank=0,  # Will be set after sorting
            raw_text=raw_texts[idx] if raw_texts and idx < len(raw_texts) else None
        )
        
        ranked_offers.append(ranked_offer)
    
    # Sort by value_index descending
    ranked_offers.sort(key=lambda x: x.value_index, reverse=True)
    
    # Assign ranks (1 = best value)
    for idx, offer in enumerate(ranked_offers, start=1):
        offer.rank = idx
    
    return ranked_offers

