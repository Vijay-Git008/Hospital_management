from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..db.database import get_db
from ..db.models import Negotiation, NegotiationStep
from ..models.schemas import NegotiationOut, NegotiationStepOut

router = APIRouter(prefix="/api/negotiation", tags=["Negotiation Trails"])

@router.get("/history", response_model=List[NegotiationOut])
def get_negotiation_history(db: Session = Depends(get_db)):
    """Retrieves all previous negotiation results and their explainable reasoning trees."""
    return db.query(Negotiation).order_by(Negotiation.created_at.desc()).all()

@router.get("/{negotiation_id}/steps", response_model=List[NegotiationStepOut])
def get_negotiation_steps(negotiation_id: str, db: Session = Depends(get_db)):
    """Retrieves the granular CNP exchange logs (CFP -> BID -> AWARD/REJECT) for an allocation."""
    steps = db.query(NegotiationStep).filter(
        NegotiationStep.negotiation_id == negotiation_id
    ).order_by(NegotiationStep.created_at.asc()).all()
    return steps
