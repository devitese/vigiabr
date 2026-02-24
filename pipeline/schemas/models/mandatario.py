"""Mandatario (elected official) — SQLAlchemy model and Pydantic schema."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import Field
from sqlalchemy import CheckConstraint, Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, BaseEntitySchema, BaseSchema, TimestampMixin, UUIDPrimaryKeyMixin


class Mandatario(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "mandatarios"

    id_tse: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    nome_civil: Mapped[Optional[str]] = mapped_column(String(255))
    cargo: Mapped[str] = mapped_column(String(100), nullable=False)
    uf: Mapped[str] = mapped_column(String(2), nullable=False)
    partido_sigla: Mapped[Optional[str]] = mapped_column(String(20))
    mandato_inicio: Mapped[Optional[date]] = mapped_column(Date)
    mandato_fim: Mapped[Optional[date]] = mapped_column(Date)
    sci_score: Mapped[Optional[int]] = mapped_column(Integer)
    cpf_hash: Mapped[Optional[str]] = mapped_column(String(64))

    # Relationships
    bens: Mapped[list] = relationship("BemPatrimonial", back_populates="mandatario")
    emendas: Mapped[list] = relationship("Emenda", back_populates="autor")
    inconsistencias: Mapped[list] = relationship("Inconsistencia", back_populates="mandatario")

    __table_args__ = (
        CheckConstraint("sci_score BETWEEN 0 AND 1000", name="ck_mandatario_sci_range"),
    )


class MandatarioSchema(BaseEntitySchema):
    id_tse: str
    nome: str
    nome_civil: Optional[str] = None
    cargo: str
    uf: str = Field(max_length=2)
    partido_sigla: Optional[str] = None
    mandato_inicio: Optional[date] = None
    mandato_fim: Optional[date] = None
    sci_score: Optional[int] = Field(None, ge=0, le=1000)
    cpf_hash: Optional[str] = None


class MandatarioCreateSchema(BaseSchema):
    id_tse: str
    nome: str
    nome_civil: Optional[str] = None
    cargo: str
    uf: str = Field(max_length=2)
    partido_sigla: Optional[str] = None
    mandato_inicio: Optional[date] = None
    mandato_fim: Optional[date] = None
    cpf_hash: Optional[str] = None
