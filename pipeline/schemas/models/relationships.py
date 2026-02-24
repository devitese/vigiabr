"""Relationship / junction table models for graph-like associations in PostgreSQL."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, BaseSchema, TimestampMixin, UUIDPrimaryKeyMixin


# --- Mandatario ↔ Partido (FILIADO_A) ---

class MandatarioFiliacao(Base):
    __tablename__ = "mandatario_filiacoes"

    mandatario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mandatarios.id"), primary_key=True
    )
    partido_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("partidos.id"), primary_key=True
    )
    data_filiacao: Mapped[date] = mapped_column(Date, primary_key=True)
    data_desfiliacao: Mapped[Optional[date]] = mapped_column(Date)


class MandatarioFiliacaoSchema(BaseSchema):
    mandatario_id: uuid.UUID
    partido_id: uuid.UUID
    data_filiacao: date
    data_desfiliacao: Optional[date] = None


# --- Mandatario → PessoaFisica (TEM_FAMILIAR) ---

class MandatarioFamiliar(Base):
    __tablename__ = "mandatario_familiares"

    mandatario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mandatarios.id"), primary_key=True
    )
    pessoa_fisica_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pessoas_fisicas.id"), primary_key=True
    )
    grau: Mapped[str] = mapped_column(String(50), nullable=False)


class MandatarioFamiliarSchema(BaseSchema):
    mandatario_id: uuid.UUID
    pessoa_fisica_id: uuid.UUID
    grau: str


# --- Mandatario → PessoaFisica (CONTRATOU) ---

class MandatarioContratacao(Base):
    __tablename__ = "mandatario_contratacoes"

    mandatario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mandatarios.id"), primary_key=True
    )
    pessoa_fisica_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pessoas_fisicas.id"), primary_key=True
    )
    cargo: Mapped[Optional[str]] = mapped_column(String(100))
    salario: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    data_inicio: Mapped[Optional[date]] = mapped_column(Date)
    gabinete: Mapped[bool] = mapped_column(Boolean, default=False)


class MandatarioContratacaoSchema(BaseSchema):
    mandatario_id: uuid.UUID
    pessoa_fisica_id: uuid.UUID
    cargo: Optional[str] = None
    salario: Optional[Decimal] = None
    data_inicio: Optional[date] = None
    gabinete: bool = False


# --- PessoaFisica → Empresa (SOCIO_DE) ---

class PessoaEmpresaSocio(Base):
    __tablename__ = "pessoa_empresa_socios"

    pessoa_fisica_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pessoas_fisicas.id"), primary_key=True
    )
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("empresas.id"), primary_key=True
    )
    percentual_cotas: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    data_entrada: Mapped[Optional[date]] = mapped_column(Date)
    data_saida: Mapped[Optional[date]] = mapped_column(Date)


class PessoaEmpresaSocioSchema(BaseSchema):
    pessoa_fisica_id: uuid.UUID
    empresa_id: uuid.UUID
    percentual_cotas: Optional[Decimal] = None
    data_entrada: Optional[date] = None
    data_saida: Optional[date] = None


# --- Doacao (RECEBEU_DOACAO) ---

class Doacao(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "doacoes"

    mandatario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mandatarios.id"), nullable=False
    )
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    data: Mapped[Optional[date]] = mapped_column(Date)
    eleicao_ano: Mapped[Optional[int]] = mapped_column(Integer)
    origem: Mapped[Optional[str]] = mapped_column(String(10))
    doador_nome: Mapped[Optional[str]] = mapped_column(String(255))
    doador_cpf_cnpj_hash: Mapped[Optional[str]] = mapped_column(String(64))


class DoacaoSchema(BaseSchema):
    mandatario_id: uuid.UUID
    valor: Decimal
    data: Optional[date] = None
    eleicao_ano: Optional[int] = None
    origem: Optional[str] = None
    doador_nome: Optional[str] = None
    doador_cpf_cnpj_hash: Optional[str] = None
