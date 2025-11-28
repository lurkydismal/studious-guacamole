from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from contact import ContactCreate, ContactOut, Contact
from db import get_db
from service import find_or_create_lead, assign_operator_for_source_atomic

from sources.source import Source

router = APIRouter()


@router.post("/contacts", response_model=ContactOut)
def create_contact(payload: ContactCreate, db: Session = Depends(get_db)):
    """
    Create a contact:
    1) find-or-create lead,
    2) ensure source exists,
    3) attempt atomic assignment (row-level locks),
    4) create contact record (assigned or unassigned).
    Behavior: if no eligible operator -> contact is created without assigned operator.
    """
    src_name = payload.source
    external_id = payload.external_id
    phone = payload.phone
    email = payload.email

    # 1) find or create lead
    lead = find_or_create_lead(db, external_id, phone, email)

    # 2) ensure source exists (create if missing)
    source = db.scalar(select(Source).where(Source.name == src_name))
    if not source:
        source = Source(name=src_name)
        db.add(source)
        db.commit()
        db.refresh(source)

    # 3) atomic assignment + contact creation inside one transaction
    # Use Session.begin() to group FOR UPDATE and insert into a single transaction.
    with db.begin():
        # attempt to choose operator and increment workload atomically
        op = assign_operator_for_source_atomic(db, src_name)

        # create contact linked to lead, source and assigned operator (or None)
        contact = Contact(
            lead_id=lead.id, source_id=source.id, assigned_to=(op.id if op else None)
        )
        db.add(contact)
        # changes (operator workload increment + contact insert) will be committed at context exit

    # 4) refresh to get assigned id / timestamps
    db.refresh(contact)

    return ContactOut(contact_id=contact.id, assigned_to=(op.id if op else None))


# @app.post("/contacts", response_model=ContactOut)
# def create_contact(payload: ContactCreate, db: Session = Depends(get_db)):
#     """
#     Create a new contact (interaction from a source).
#     Example payload:
#     {
#       "source": "telegram_bot_1",
#       "external_id": "ext-123",   # optional
#       "phone": "+7700...",        # optional
#       "email": "a@b.com"          # optional
#     }
#     """
#     src_name = payload.source
#     external_id = payload.external_id
#     phone = payload.phone
#     email = payload.email
#
#     # Find or create the lead
#     lead = find_or_create_lead(db, external_id, phone, email)
#
#     # Ensure source exists
#     source = db.scalar(select(Source).where(Source.name == src_name))
#     if not source:
#         source = Source(name=src_name)
#         db.add(source)
#         db.commit()
#         db.refresh(source)
#
#     # Attempt to assign an operator
#     # Note: In production, wrap in a transaction and consider row-level locks (SELECT ... FOR UPDATE)
#     op = assign_operator_for_source(db, src_name)
#
#     # Create contact entry
#     contact = Contact(
#         lead_id=lead.id, source_id=source.id, assigned_to=(op.id if op else None)
#     )
#     db.add(contact)
#
#     if op:
#         # Increment operator workload
#         op.workload += 1
#         db.add(op)
#
#     db.commit()
#     db.refresh(contact)
#     return {"contact_id": contact.id, "assigned_to": (op.id if op else None)}
