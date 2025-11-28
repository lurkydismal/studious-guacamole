import random
from fastapi import FastAPI, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import SessionLocal, engine
from models import Base, Lead, Source, SourceOperator, Operator, Contact
from schemas import (
    ContactCreate,
    ContactOut,
    OperatorCreate,
    OperatorOut,
    LeadCreate,
    LeadOut,
)

# Create all tables in the database
Base.metadata.create_all(bind=engine)

app = FastAPI()


def get_db():
    """Provide a database session to endpoints and close it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
    """Simple health check endpoint."""
    return {"status": "ok"}


def assign_operator_for_source(db: Session, source_name: str) -> Operator | None:
    """
    Return a selected operator or None if none are available.
    Algorithm:
    1. Fetch (operator, weight) pairs for the source.
    2. Filter only active operators whose workload is less than their limit.
    3. Pick one operator randomly based on weight.
    """
    source = db.scalar(select(Source).where(Source.name == source_name))
    if not source:
        return None

    # Join SourceOperator -> Operator
    rows = db.execute(
        select(SourceOperator, Operator)
        .join(Operator, SourceOperator.operator_id == Operator.id)
        .where(SourceOperator.source_id == source.id)
    ).all()

    # Keep only eligible operators
    choices = []
    for so, op in rows:
        if op.active and (op.workload < op.limit):
            if so.weight > 0:
                choices.append((op, so.weight))

    if not choices:
        return None

    # Weighted random selection
    total = sum(w for _, w in choices)
    r = random.uniform(0, total)
    upto = 0.0
    for op, w in choices:
        upto += w
        if r <= upto:
            return op
    return choices[-1][0]  # fallback to last operator


@app.post("/operators", response_model=OperatorOut)
def create_operator(op: OperatorCreate, db: Session = Depends(get_db)):
    """Create a new operator with given name and workload limit."""
    new_op = Operator(name=op.name, limit=op.limit, workload=0)
    db.add(new_op)
    db.commit()
    db.refresh(new_op)
    return new_op


@app.get("/operators", response_model=list[OperatorOut])
def list_operators(db: Session = Depends(get_db)):
    """List all operators."""
    return db.query(Operator).all()


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


@app.post("/leads", response_model=LeadOut)
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


@app.get("/leads", response_model=list[LeadOut])
def list_leads(db: Session = Depends(get_db)):
    """List all leads, ordered by creation date descending."""
    return db.query(Lead).order_by(Lead.created_at.desc()).all()


@app.post("/contacts", response_model=ContactOut)
def create_contact(payload: ContactCreate, db: Session = Depends(get_db)):
    """
    Create a new contact (interaction from a source).
    Example payload:
    {
      "source": "telegram_bot_1",
      "external_id": "ext-123",   # optional
      "phone": "+7700...",        # optional
      "email": "a@b.com"          # optional
    }
    """
    src_name = payload.source
    external_id = payload.external_id
    phone = payload.phone
    email = payload.email

    # Find or create the lead
    lead = find_or_create_lead(db, external_id, phone, email)

    # Ensure source exists
    source = db.scalar(select(Source).where(Source.name == src_name))
    if not source:
        source = Source(name=src_name)
        db.add(source)
        db.commit()
        db.refresh(source)

    # Attempt to assign an operator
    # Note: In production, wrap in a transaction and consider row-level locks (SELECT ... FOR UPDATE)
    op = assign_operator_for_source(db, src_name)

    # Create contact entry
    contact = Contact(
        lead_id=lead.id, source_id=source.id, assigned_to=(op.id if op else None)
    )
    db.add(contact)

    if op:
        # Increment operator workload
        op.workload += 1
        db.add(op)

    db.commit()
    db.refresh(contact)
    return {"contact_id": contact.id, "assigned_to": (op.id if op else None)}
