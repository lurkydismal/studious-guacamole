from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from pydantic import BaseModel

from model_base import Base

from operators.operator import Operator
from leads.lead import Lead
from sources.source import Source


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"))
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc)
    )
    assigned_to: Mapped[int | None] = mapped_column(
        ForeignKey("operators.id")
    )  # Operator assigned for this contact

    lead: Mapped["Lead"] = relationship(back_populates="contacts")
    source: Mapped["Source"] = relationship()  # Source/bot for this contact
    operator: Mapped["Operator | None"] = relationship(back_populates="contacts")


class ContactCreate(BaseModel):
    source: str
    external_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class ContactOut(BaseModel):
    contact_id: int
    assigned_to: Optional[int] = None
