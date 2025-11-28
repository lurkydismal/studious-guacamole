from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from db import get_db

from leads.lead import Lead, LeadCreate, LeadOut
from service import assign_lead_simple

router = APIRouter()


@router.post("/leads", response_model=LeadOut)
def create_lead(l_in: LeadCreate, db: Session = Depends(get_db)):
    """
    Create a new lead from input data.
    Automatically assign operator using simple assignment logic.
    """
    new_lead = Lead(source=l_in.source)
    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)

    # Try automatic assignment (replace with weighted logic later)
    assign_lead_simple(db, new_lead)

    return new_lead


@router.get("/leads", response_model=list[LeadOut])
def list_leads(db: Session = Depends(get_db)):
    """List all leads, ordered by creation date descending."""
    return db.query(Lead).order_by(Lead.created_at.desc()).all()
