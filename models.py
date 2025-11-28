from sqlalchemy import DateTime, ForeignKey
from typing import List
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from datetime import datetime, timezone

Base = declarative_base()


class Operator(Base):
    __tablename__ = "operators"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column()
    limit: Mapped[int] = mapped_column()  # Max allowed workload
    workload: Mapped[int] = mapped_column(default=0)
    leads: Mapped[list["Lead"]] = relationship(back_populates="operator")

    # связи
    source_weights: Mapped[List["SourceOperator"]] = relationship(
        back_populates="operator"
    )
    contacts: Mapped[List["Contact"]] = relationship(back_populates="operator")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source: Mapped[str] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc)
    )

    assigned_to: Mapped[int | None] = mapped_column(
        ForeignKey("operators.id"), nullable=True
    )
    operator: Mapped["Operator | None"] = relationship(back_populates="leads")

    contacts: Mapped[List["Contact"]] = relationship(back_populates="lead")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(unique=True, index=True)

    operators: Mapped[List["SourceOperator"]] = relationship(back_populates="source")


class SourceOperator(Base):
    __tablename__ = "source_operators"
    # association table: для каждого source указываются операторы и веса
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    operator_id: Mapped[int] = mapped_column(ForeignKey("operators.id"))
    weight: Mapped[int] = mapped_column()  # числовой вес / компетенция

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
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("operators.id"))

    lead: Mapped["Lead"] = relationship(back_populates="contacts")
    source: Mapped["Source"] = relationship()
    operator: Mapped["Operator | None"] = relationship(back_populates="contacts")
