"""ContratoGov (government contract) — SQLAlchemy model and Pydantic schema."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, BaseEntitySchema, BaseSchema, TimestampMixin, UUIDPrimaryKeyMixin


class ContratoGov(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "contratos_gov"

    numero: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    objeto: Mapped[Optional[str]] = mapped_column(Text)
    valor: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    orgao_contratante: Mapped[Optional[str]] = mapped_column(String(255))
    data_assinatura: Mapped[Optional[date]] = mapped_column(Date)
    empresa_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("empresas.id")
    )


class ContratoGovSchema(BaseEntitySchema):
    numero: str
    objeto: Optional[str] = None
    valor: Optional[Decimal] = None
    orgao_contratante: Optional[str] = None
    data_assinatura: Optional[date] = None
    empresa_id: Optional[uuid.UUID] = None


class ContratoGovCreateSchema(BaseSchema):
    numero: str
    objeto: Optional[str] = None
    valor: Optional[Decimal] = None
    orgao_contratante: Optional[str] = None
    data_assinatura: Optional[date] = None
    empresa_id: Optional[uuid.UUID] = None
