from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from db import SessionLocal, engine
from models import Base, Operator, Lead
from schemas import OperatorCreate, OperatorOut, LeadCreate, LeadOut

Base.metadata.create_all(bind=engine)

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
    return {"status": "ok"}


@app.post("/operators", response_model=OperatorOut)
def create_operator(op: OperatorCreate, db: Session = Depends(get_db)):
    new_op = Operator(name=op.name, limit=op.limit, workload=0)
    db.add(new_op)
    db.commit()
    db.refresh(new_op)
    return new_op


@app.get("/operators", response_model=list[OperatorOut])
def list_operators(db: Session = Depends(get_db)):
    return db.query(Operator).all()


def assign_lead_simple(db: Session, lead: Lead) -> None:
    """
    Minimal assignment: pick the first eligible operator (workload < limit).
    Replace this with weighted logic later.
    """
    op = (
        db.query(Operator)
        .filter(Operator.workload < Operator.limit)
        .order_by(Operator.id)
        .first()
    )
    if not op:
        return  # Nothing available; leave unassigned
    lead.assigned_to = op.id
    op.workload = op.workload + 1
    db.add(op)
    db.add(lead)
    db.commit()
    db.refresh(lead)


@app.post("/leads", response_model=LeadOut)
def create_lead(l_in: LeadCreate, db: Session = Depends(get_db)):
    new_lead = Lead(source=l_in.source)
    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)

    # try automatic assignment (simple). Swap with weighted function when ready.
    assign_lead_simple(db, new_lead)

    return new_lead


@app.get("/leads", response_model=list[LeadOut])
def list_leads(db: Session = Depends(get_db)):
    return db.query(Lead).order_by(Lead.created_at.desc()).all()
