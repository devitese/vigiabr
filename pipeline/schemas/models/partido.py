"""Partido (political party) — SQLAlchemy model and Pydantic schema."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, BaseEntitySchema, BaseSchema, TimestampMixin, UUIDPrimaryKeyMixin


class Partido(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "partidos"

    sigla: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    numero_eleitoral: Mapped[Optional[int]] = mapped_column(Integer, unique=True)


class PartidoSchema(BaseEntitySchema):
    sigla: str
    nome: str
    numero_eleitoral: Optional[int] = None


class PartidoCreateSchema(BaseSchema):
    sigla: str
    nome: str
    numero_eleitoral: Optional[int] = None
