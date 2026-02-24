"""ProcessoJudicial (lawsuit) — SQLAlchemy model and Pydantic schema."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, BaseEntitySchema, BaseSchema, TimestampMixin, UUIDPrimaryKeyMixin


class ProcessoJudicial(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "processos_judiciais"

    numero_cnj: Mapped[str] = mapped_column(String(25), unique=True, nullable=False)
    tipo: Mapped[Optional[str]] = mapped_column(String(100))
    tribunal: Mapped[str] = mapped_column(String(50), nullable=False)
    situacao: Mapped[Optional[str]] = mapped_column(String(100))
    valor_causa: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))


class ProcessoJudicialSchema(BaseEntitySchema):
    numero_cnj: str
    tipo: Optional[str] = None
    tribunal: str
    situacao: Optional[str] = None
    valor_causa: Optional[Decimal] = None


class ProcessoJudicialCreateSchema(BaseSchema):
    numero_cnj: str
    tipo: Optional[str] = None
    tribunal: str
    situacao: Optional[str] = None
    valor_causa: Optional[Decimal] = None
