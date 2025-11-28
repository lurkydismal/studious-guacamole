from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column

from model_base import Base
from source import Source

from operators.operator import Operator


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
