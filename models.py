from sqlalchemy import DateTime, ForeignKey
from typing import List
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from datetime import datetime, timezone

Base = declarative_base()


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


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(unique=True, index=True)  # Bot/source name

    operators: Mapped[List["SourceOperator"]] = relationship(
        back_populates="source"
    )  # Operators linked to this source with weights


class SourceOperator(Base):
    __tablename__ = "source_operators"
    # Association table: defines which operators work with which sources and their respective weights
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    operator_id: Mapped[int] = mapped_column(ForeignKey("operators.id"))
    weight: Mapped[int] = (
        mapped_column()
    )  # Numeric weight / competency for traffic distribution

    source: Mapped["Source"] = relationship(back_populates="operators")
    operator: Mapped["Operator"] = relationship(back_populates="source_weights")


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
