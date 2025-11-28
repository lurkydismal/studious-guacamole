import random

from sqlalchemy.orm import Session

from sqlalchemy import select

from operators.operator import Operator
from sources.operator import SourceOperator
from sources.source import Source


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
