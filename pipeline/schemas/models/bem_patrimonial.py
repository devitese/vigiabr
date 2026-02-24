"""BemPatrimonial (declared asset) — SQLAlchemy model and Pydantic schema."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, BaseEntitySchema, BaseSchema, TimestampMixin, UUIDPrimaryKeyMixin


class BemPatrimonial(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "bens_patrimoniais"

    mandatario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mandatarios.id"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(100), nullable=False)
    descricao: Mapped[Optional[str]] = mapped_column(Text)
    valor_declarado: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    ano_eleicao: Mapped[int] = mapped_column(Integer, nullable=False)

    mandatario = relationship("Mandatario", back_populates="bens")


class BemPatrimonialSchema(BaseEntitySchema):
    mandatario_id: uuid.UUID
    tipo: str
    descricao: Optional[str] = None
    valor_declarado: Decimal
    ano_eleicao: int


class BemPatrimonialCreateSchema(BaseSchema):
    mandatario_id: uuid.UUID
    tipo: str
    descricao: Optional[str] = None
    valor_declarado: Decimal
    ano_eleicao: int
