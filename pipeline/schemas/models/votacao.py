"""Votacao (roll-call vote) and MandatarioVoto (individual vote) — models and schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, BaseEntitySchema, BaseSchema, TimestampMixin, UUIDPrimaryKeyMixin


class TipoVoto(StrEnum):
    SIM = "Sim"
    NAO = "Não"
    ABSTENCAO = "Abstenção"
    AUSENTE = "Ausente"
    OBSTRUCAO = "Obstrução"


class Votacao(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "votacoes"

    id_externo: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    data: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    descricao: Mapped[Optional[str]] = mapped_column(Text)
    tipo_proposicao: Mapped[Optional[str]] = mapped_column(String(50))
    resultado: Mapped[Optional[str]] = mapped_column(String(50))


class MandatarioVoto(Base):
    __tablename__ = "mandatario_votos"

    mandatario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mandatarios.id"), primary_key=True
    )
    votacao_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("votacoes.id"), primary_key=True
    )
    voto: Mapped[str] = mapped_column(String(20), nullable=False)
    data: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class VotacaoSchema(BaseEntitySchema):
    id_externo: str
    data: datetime
    descricao: Optional[str] = None
    tipo_proposicao: Optional[str] = None
    resultado: Optional[str] = None


class MandatarioVotoSchema(BaseSchema):
    mandatario_id: uuid.UUID
    votacao_id: uuid.UUID
    voto: TipoVoto
    data: Optional[datetime] = None
