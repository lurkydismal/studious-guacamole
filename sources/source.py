from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import List

from model_base import Base
from .operator import SourceOperator


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(unique=True, index=True)  # Bot/source name

    operators: Mapped[List["SourceOperator"]] = relationship(
        back_populates="source"
    )  # Operators linked to this source with weights
