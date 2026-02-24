"""Raw JSONL models for Camara dos Deputados spider output."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, HttpUrl

__all__ = [
    "CamaraDeputadoRaw",
    "CamaraVotacaoRaw",
    "CamaraVotoRaw",
    "CamaraDespesaRaw",
    "CamaraProposicaoRaw",
    "CamaraFrenteRaw",
]


class CamaraDeputadoRaw(BaseModel):
    type: Literal["deputado"] = "deputado"
    id: int
    nome: str
    nome_civil: Optional[str] = None
    cpf: Optional[str] = None
    sigla_partido: str
    sigla_uf: str
    id_legislatura: Optional[int] = None
    url_foto: Optional[HttpUrl] = None
    email: Optional[str] = None
    data_nascimento: Optional[date] = None
    sexo: Optional[Literal["M", "F"]] = None


class CamaraVotoRaw(BaseModel):
    id_deputado: int
    voto: Literal["Sim", "Não", "Abstenção", "Ausente", "Obstrução"]


class CamaraVotacaoRaw(BaseModel):
    type: Literal["votacao"] = "votacao"
    id_votacao: str
    data: datetime
    descricao: str
    id_proposicao: Optional[int] = None
    votos: list[CamaraVotoRaw] = []


class CamaraDespesaRaw(BaseModel):
    type: Literal["despesa"] = "despesa"
    id_deputado: int
    ano: int
    mes: int
    tipo_despesa: str
    valor_documento: Optional[Decimal] = None
    valor_liquido: Decimal
    valor_glosa: Optional[Decimal] = None
    cnpj_cpf_fornecedor: Optional[str] = None
    nome_fornecedor: Optional[str] = None
    numero_documento: Optional[str] = None
    url_documento: Optional[HttpUrl] = None


class CamaraProposicaoRaw(BaseModel):
    type: Literal["proposicao"] = "proposicao"
    id: int
    tipo: str
    numero: int
    ano: int
    ementa: Optional[str] = None
    situacao: Optional[str] = None
    tema: Optional[str] = None
    id_autor: Optional[int] = None


class CamaraFrenteRaw(BaseModel):
    type: Literal["frente"] = "frente"
    id: int
    titulo: str
    id_legislatura: Optional[int] = None
    membros: list[int] = []
