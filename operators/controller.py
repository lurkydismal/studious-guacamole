from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import get_db
from .operator import OperatorCreate, OperatorOut

from operators.operator import Operator

router = APIRouter()


@router.post("/operators", response_model=OperatorOut)
def create_operator(op: OperatorCreate, db: Session = Depends(get_db)):
    """Create a new operator with given name and workload limit."""
    new_op = Operator(name=op.name, limit=op.limit, workload=0)
    db.add(new_op)
    db.commit()
    db.refresh(new_op)
    return new_op


@router.get("/operators", response_model=list[OperatorOut])
def list_operators(db: Session = Depends(get_db)):
    """List all operators."""
    return db.query(Operator).all()
