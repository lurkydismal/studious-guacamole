from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import DateTime, ForeignKey
from pydantic import BaseModel, ConfigDict

from model_base import Base

from contacts.contact import Contact
from operators.operator import Operator


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source: Mapped[str] = mapped_column(index=True)  # Source/bot from which lead came
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc)
    )

    assigned_to: Mapped[int | None] = mapped_column(
        ForeignKey("operators.id"), nullable=True
    )  # Operator currently assigned to this lead
    operator: Mapped["Operator | None"] = relationship(back_populates="leads")

    contacts: Mapped[List["Contact"]] = relationship(
        back_populates="lead"
    )  # All contact events from this lead


class LeadCreate(BaseModel):
    source: str


class LeadOut(BaseModel):
    id: int
    source: str
    created_at: datetime
    assigned_to: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
