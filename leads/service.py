from sqlalchemy.orm import Session
from sqlalchemy import select

from operators.operator import Operator
from leads.lead import Lead


def find_or_create_lead(
    db: Session, external_id: str | None, phone: str | None, email: str | None
) -> Lead:
    """
    Find an existing lead by external_id, phone, or email.
    If none found, create a new Lead.
    """
    if external_id:
        lead = db.scalar(select(Lead).where(Lead.external_id == external_id))
        if lead:
            return lead
    if phone:
        lead = db.scalar(select(Lead).where(Lead.phone == phone))
        if lead:
            return lead
    if email:
        lead = db.scalar(select(Lead).where(Lead.email == email))
        if lead:
            return lead

    # If no existing lead found, create a new one
    new = Lead(external_id=external_id, phone=phone, email=email)
    db.add(new)
    db.commit()
    db.refresh(new)
    return new


def assign_lead_simple(db: Session, lead: Lead) -> None:
    """
    Minimal lead assignment: pick the first eligible operator
    (whose workload < limit).
    Replace this with weighted assignment logic later.
    """
    op = (
        db.query(Operator)
        .filter(Operator.workload < Operator.limit)
        .order_by(Operator.id)
        .first()
    )
    if not op:
        return  # No available operator, leave unassigned

    # Assign operator and increment workload
    lead.assigned_to = op.id
    op.workload += 1
    db.add(op)
    db.add(lead)
    db.commit()
    db.refresh(lead)
