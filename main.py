import random
from fastapi import FastAPI, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import SessionLocal, engine
from models import Base, Lead, Source, SourceOperator, Operator, Contact
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


def assign_operator_for_source(db: Session, source_name: str) -> Operator | None:
    """
    Вернуть выбранного оператора или None, если никого нет.
    Алгоритм: получить пары (operator, weight) для source, фильтровать active and workload < limit,
    затем weighted random by weight.
    """
    source = db.scalar(select(Source).where(Source.name == source_name))
    if not source:
        return None

    # join source_operators -> operator
    rows = db.execute(
        select(SourceOperator, Operator)
        .join(Operator, SourceOperator.operator_id == Operator.id)
        .where(SourceOperator.source_id == source.id)
    ).all()

    # собрать только eligible
    choices = []
    for so, op in rows:
        if op.active and (op.workload < op.limit):
            if so.weight > 0:
                choices.append((op, so.weight))

    if not choices:
        return None

    total = sum(w for _, w in choices)
    r = random.uniform(0, total)
    upto = 0.0
    for op, w in choices:
        upto += w
        if r <= upto:
            return op
    return choices[-1][0]


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


def find_or_create_lead(
    db: Session, external_id: str | None, phone: str | None, email: str | None
) -> Lead:
    # поиск по внешнему id -> телефону -> почте
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
    # если не найден — создаём
    new = Lead(external_id=external_id, phone=phone, email=email)
    db.add(new)
    db.commit()
    db.refresh(new)
    return new


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


@app.post("/contacts")
def create_contact(payload: dict, db: Session = Depends(get_db)):
    """
    payload example:
    {
      "source": "telegram_bot_1",
      "external_id": "ext-123",   # optional
      "phone": "+7700...",        # optional
      "email": "a@b.com"         # optional
    }
    """
    src_name = payload["source"]
    external_id = payload.get("external_id")
    phone = payload.get("phone")
    email = payload.get("email")

    lead = find_or_create_lead(db, external_id, phone, email)
    # ensure source exists
    source = db.scalar(select(Source).where(Source.name == src_name))
    if not source:
        source = Source(name=src_name)
        db.add(source)
        db.commit()
        db.refresh(source)

    # попытка назначить оператора
    # В идеале надо делать это в транзакции и брать lock на строку оператора (SELECT ... FOR UPDATE)
    # Пример ниже упрощённый; для production используйте row-level locks или отдельный счетчик в БД.
    op = assign_operator_for_source(db, src_name)

    contact = Contact(
        lead_id=lead.id, source_id=source.id, assigned_to=(op.id if op else None)
    )
    db.add(contact)
    if op:
        # увеличить нагрузку оператора
        op.workload = op.workload + 1
        db.add(op)
    db.commit()
    db.refresh(contact)
    return {"contact_id": contact.id, "assigned_to": (op.id if op else None)}
