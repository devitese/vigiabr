"""Raw JSONL models for CNJ DataJud spider output."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel

__all__ = [
    "CnjProcessoRaw",
    "CnjParteRaw",
]


class CnjParteRaw(BaseModel):
    nome: str
    cpf_cnpj: Optional[str] = None
    tipo: Literal["Autor", "Reu", "Terceiro"]


class CnjProcessoRaw(BaseModel):
    type: Literal["processo"] = "processo"
    numero_cnj: str
    classe: str
    assuntos: list[str] = []
    tribunal: str
    vara: Optional[str] = None
    data_ajuizamento: Optional[date] = None
    situacao: Optional[str] = None
    valor_causa: Optional[Decimal] = None
    partes: list[CnjParteRaw] = []
