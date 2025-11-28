from sqlalchemy import DateTime, ForeignKey
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
