"""ProjetoLei (bill/legislation) — SQLAlchemy model and Pydantic schema."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, BaseEntitySchema, BaseSchema, TimestampMixin, UUIDPrimaryKeyMixin


class ProjetoLei(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projetos_lei"

    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    ano: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    ementa: Mapped[Optional[str]] = mapped_column(Text)
    tema: Mapped[Optional[str]] = mapped_column(String(100))
    situacao: Mapped[Optional[str]] = mapped_column(String(100))

    __table_args__ = (
        UniqueConstraint("tipo", "numero", "ano", name="uq_projeto_lei_tipo_numero_ano"),
    )


class ProjetoLeiSchema(BaseEntitySchema):
    numero: int
    ano: int
    tipo: str
    ementa: Optional[str] = None
    tema: Optional[str] = None
    situacao: Optional[str] = None


class ProjetoLeiCreateSchema(BaseSchema):
    numero: int
    ano: int
    tipo: str
    ementa: Optional[str] = None
    tema: Optional[str] = None
    situacao: Optional[str] = None
