"""Inconsistencia (detected inconsistency) — SQLAlchemy model and Pydantic schema."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from pydantic import Field
from sqlalchemy import ARRAY, CheckConstraint, Date, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, BaseEntitySchema, BaseSchema, TimestampMixin, UUIDPrimaryKeyMixin


class Inconsistencia(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "inconsistencias"

    tipo: Mapped[str] = mapped_column(String(100), nullable=False)
    descricao_neutra: Mapped[str] = mapped_column(Text, nullable=False)
    metrica: Mapped[Optional[str]] = mapped_column(String(255))
    score_impacto: Mapped[int] = mapped_column(Integer, nullable=False)
    fontes: Mapped[list[str]] = mapped_column(ARRAY(String), server_default="{}", nullable=False)
    data_deteccao: Mapped[date] = mapped_column(Date, server_default=text("CURRENT_DATE"), nullable=False)
    mandatario_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mandatarios.id")
    )

    mandatario = relationship("Mandatario", back_populates="inconsistencias")

    __table_args__ = (
        CheckConstraint(
            "score_impacto BETWEEN 0 AND 250", name="ck_inconsistencia_score_range"
        ),
    )


class InconsistenciaSchema(BaseEntitySchema):
    tipo: str
    descricao_neutra: str
    metrica: Optional[str] = None
    score_impacto: int = Field(ge=0, le=250)
    fontes: list[str] = []
    data_deteccao: date
    mandatario_id: Optional[uuid.UUID] = None


class InconsistenciaCreateSchema(BaseSchema):
    tipo: str
    descricao_neutra: str
    metrica: Optional[str] = None
    score_impacto: int = Field(ge=0, le=250)
    fontes: list[str] = []
    mandatario_id: Optional[uuid.UUID] = None
