import random

# from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sources.source import Source
from sources.operator import SourceOperator
from operators.operator import Operator
from leads.lead import Lead


def find_or_create_lead(
    db: Session, external_id: str | None, phone: str | None, email: str | None
) -> Lead:
    """
    Find existing lead by external_id -> phone -> email. If none found, create one.
    To avoid race creating duplicate leads, this function handles IntegrityError
    when unique constraints are present (e.g. external_id unique).
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

    # Not found -> create. Unique constraints may cause IntegrityError in a race.
    new = Lead(external_id=external_id, phone=phone, email=email)
    db.add(new)
    try:
        db.commit()
        db.refresh(new)
        return new
    except IntegrityError:
        # Another transaction created the same lead concurrently.
        db.rollback()
        # Re-query deterministically by the same priority
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
        # If still missing, raise — unexpected
        raise


def assign_operator_for_source_atomic(db: Session, source_name: str) -> Operator | None:
    """
    Atomically pick an eligible operator for `source_name` and increment its workload.
    Uses row-level locks to make increment atomic and avoid race conditions.
    Returns the chosen Operator instance (already updated in the DB session), or None.
    Important: this must be called inside a transaction (db.begin()) so that FOR UPDATE can lock rows.
    """
    # 1) find source
    source = db.scalar(select(Source).where(Source.name == source_name))
    if not source:
        return None

    # 2) fetch source->operator configuration (weights)
    so_rows = (
        db.execute(select(SourceOperator).where(SourceOperator.source_id == source.id))
        .scalars()
        .all()
    )

    if not so_rows:
        return None

    # 3) collect operator ids with positive weight
    candidate_ids = [so.operator_id for so in so_rows if (so.weight or 0) > 0]
    if not candidate_ids:
        return None

    # 4) lock operator rows for update (row-level lock)
    #    This prevents two transactions from choosing the same operator above its limit.
    locked_ops = (
        db.execute(
            select(Operator).where(Operator.id.in_(candidate_ids)).with_for_update()
        )
        .scalars()
        .all()
    )

    # 5) build mapping operator_id -> weight
    weight_map = {so.operator_id: so.weight for so in so_rows}

    # 6) filter eligible operators (active and workload < limit)
    eligible = []
    for op in locked_ops:
        if not getattr(op, "active", True):
            continue
        if (op.workload or 0) >= (op.limit or 0):
            continue
        w = weight_map.get(op.id, 0)
        if w > 0:
            eligible.append((op, w))

    if not eligible:
        return None

    # 7) weighted random selection
    total = sum(w for _, w in eligible)
    r = random.uniform(0, total)
    upto = 0.0
    chosen_op = None
    for op, w in eligible:
        upto += w
        if r <= upto:
            chosen_op = op
            break
    if chosen_op is None:
        chosen_op = eligible[-1][0]

    # 8) increment workload in the same transaction
    chosen_op.workload = (chosen_op.workload or 0) + 1
    db.add(chosen_op)

    # Do NOT commit here; caller should be managing transaction scope.
    return chosen_op
