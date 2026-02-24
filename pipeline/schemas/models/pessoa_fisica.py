"""PessoaFisica (individual) — SQLAlchemy model and Pydantic schema."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, BaseEntitySchema, BaseSchema, TimestampMixin, UUIDPrimaryKeyMixin


class TipoPessoa(StrEnum):
    FAMILIAR = "Familiar"
    ASSESSOR = "Assessor"
    SOCIO = "Socio"
    DOADOR = "Doador"
    OUTRO = "Outro"


class PessoaFisica(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "pessoas_fisicas"

    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    cpf_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)


class PessoaFisicaSchema(BaseEntitySchema):
    nome: str
    cpf_hash: str = Field(min_length=64, max_length=64)
    tipo: TipoPessoa


class PessoaFisicaCreateSchema(BaseSchema):
    nome: str
    cpf_hash: str = Field(min_length=64, max_length=64)
    tipo: TipoPessoa
