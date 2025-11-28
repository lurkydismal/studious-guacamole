from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class OperatorCreate(BaseModel):
    name: str
    limit: int


class OperatorOut(BaseModel):
    id: int
    name: str
    limit: int
    workload: int

    class Config:
        from_attributes = True


class LeadCreate(BaseModel):
    source: str


class LeadOut(BaseModel):
    id: int
    source: str
    created_at: datetime
    assigned_to: Optional[int] = None

    class Config:
        from_attributes = True
