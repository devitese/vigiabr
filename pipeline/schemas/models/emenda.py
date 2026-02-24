"""Emenda (parliamentary amendment) — SQLAlchemy model and Pydantic schema."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, BaseEntitySchema, BaseSchema, TimestampMixin, UUIDPrimaryKeyMixin


class Emenda(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "emendas"

    numero: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    tipo: Mapped[Optional[str]] = mapped_column(String(50))
    valor_pago: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    ano: Mapped[int] = mapped_column(Integer, nullable=False)
    funcao: Mapped[Optional[str]] = mapped_column(String(100))
    autor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mandatarios.id")
    )

    autor = relationship("Mandatario", back_populates="emendas")


class EmendaSchema(BaseEntitySchema):
    numero: str
    tipo: Optional[str] = None
    valor_pago: Optional[Decimal] = None
    ano: int
    funcao: Optional[str] = None
    autor_id: Optional[uuid.UUID] = None


class EmendaCreateSchema(BaseSchema):
    numero: str
    tipo: Optional[str] = None
    valor_pago: Optional[Decimal] = None
    ano: int
    funcao: Optional[str] = None
    autor_id: Optional[uuid.UUID] = None
