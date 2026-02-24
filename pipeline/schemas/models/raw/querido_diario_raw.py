"""Raw JSONL models for Querido Diario (OKBR) spider output."""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, HttpUrl

__all__ = [
    "QueridoDiarioNomeacaoRaw",
    "QueridoDiarioPublicacaoRaw",
]


class QueridoDiarioNomeacaoRaw(BaseModel):
    type: Literal["nomeacao"] = "nomeacao"
    nome: str
    cpf: Optional[str] = None
    cargo: str
    tipo: Optional[Literal["DAS", "Nomeacao", "Exoneracao", "Substituicao"]] = None
    orgao: Optional[str] = None
    data_publicacao: date
    edicao_dou: Optional[str] = None
    secao_dou: Optional[str] = None
    url_fonte: Optional[HttpUrl] = None


class QueridoDiarioPublicacaoRaw(BaseModel):
    type: Literal["publicacao"] = "publicacao"
    data_publicacao: date
    edicao_dou: Optional[str] = None
    secao_dou: Optional[str] = None
    texto: str
    url_fonte: Optional[HttpUrl] = None
    entidades_mencionadas: list[str] = []
