"""Empresa (company) — SQLAlchemy model and Pydantic schema."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, BaseEntitySchema, BaseSchema, TimestampMixin, UUIDPrimaryKeyMixin


class Empresa(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "empresas"

    cnpj: Mapped[str] = mapped_column(String(18), unique=True, nullable=False)
    razao_social: Mapped[str] = mapped_column(String(500), nullable=False)
    cnae: Mapped[Optional[str]] = mapped_column(String(10))
    situacao: Mapped[Optional[str]] = mapped_column(String(50))
    data_abertura: Mapped[Optional[date]] = mapped_column(Date)
    capital_social: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))


class EmpresaSchema(BaseEntitySchema):
    cnpj: str
    razao_social: str
    cnae: Optional[str] = None
    situacao: Optional[str] = None
    data_abertura: Optional[date] = None
    capital_social: Optional[Decimal] = None


class EmpresaCreateSchema(BaseSchema):
    cnpj: str
    razao_social: str
    cnae: Optional[str] = None
    situacao: Optional[str] = None
    data_abertura: Optional[date] = None
    capital_social: Optional[Decimal] = None
