"""Raw JSONL models for TSE (election data) spider output."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel

__all__ = [
    "TseCandidatoRaw",
    "TseBemDeclaradoRaw",
    "TseDoacaoRaw",
    "TseDespesaCampanhaRaw",
]


class TseCandidatoRaw(BaseModel):
    type: Literal["candidato"] = "candidato"
    sequencial: str
    nome: str
    cpf: str
    numero_candidato: Optional[str] = None
    cargo: str
    sigla_partido: Optional[str] = None
    sigla_uf: str
    ano_eleicao: int
    situacao: Optional[str] = None
    resultado: Optional[str] = None


class TseBemDeclaradoRaw(BaseModel):
    type: Literal["bem_declarado"] = "bem_declarado"
    sequencial_candidato: str
    ano_eleicao: int
    tipo_bem: str
    descricao: Optional[str] = None
    valor: Decimal


class TseDoacaoRaw(BaseModel):
    type: Literal["doacao"] = "doacao"
    sequencial_candidato: str
    ano_eleicao: int
    valor: Decimal
    nome_doador: str
    cpf_cnpj_doador: Optional[str] = None
    tipo_doador: Optional[Literal["PF", "PJ", "Partido", "Candidato"]] = None
    data_receita: Optional[date] = None
    descricao: Optional[str] = None


class TseDespesaCampanhaRaw(BaseModel):
    type: Literal["despesa_campanha"] = "despesa_campanha"
    sequencial_candidato: str
    ano_eleicao: int
    valor: Decimal
    tipo_despesa: str
    nome_fornecedor: Optional[str] = None
    cnpj_cpf_fornecedor: Optional[str] = None
    data_despesa: Optional[date] = None
    descricao: Optional[str] = None
