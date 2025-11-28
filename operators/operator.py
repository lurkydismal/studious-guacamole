from typing import List

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import relationship, Mapped, mapped_column

from model_base import Base

from sources.operator import SourceOperator
from contacts.contact import Contact
from leads.lead import Lead


class Operator(Base):
    __tablename__ = "operators"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column()
    limit: Mapped[int] = mapped_column()  # Maximum allowed workload for this operator
    workload: Mapped[int] = mapped_column(default=0)  # Current number of assigned leads
    leads: Mapped[list["Lead"]] = relationship(back_populates="operator")

    # Relationships
    source_weights: Mapped[List["SourceOperator"]] = relationship(
        back_populates="operator"
    )  # Links operator to sources with weights/competencies
    contacts: Mapped[List["Contact"]] = relationship(
        back_populates="operator"
    )  # All contacts assigned to this operator


class OperatorCreate(BaseModel):
    name: str
    limit: int


class OperatorOut(BaseModel):
    id: int
    name: str
    limit: int
    workload: int

    model_config = ConfigDict(from_attributes=True)
