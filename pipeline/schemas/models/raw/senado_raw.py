"""Raw JSONL models for Senado Federal spider output."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, HttpUrl

__all__ = [
    "SenadoSenadorRaw",
    "SenadoVotacaoRaw",
    "SenadoVotoRaw",
    "SenadoMateriaRaw",
    "SenadoDespesaRaw",
]


class SenadoSenadorRaw(BaseModel):
    type: Literal["senador"] = "senador"
    codigo: int
    nome: str
    nome_completo: Optional[str] = None
    sexo: Optional[Literal["Masculino", "Feminino"]] = None
    sigla_partido: str
    sigla_uf: str
    url_foto: Optional[HttpUrl] = None
    email: Optional[str] = None
    mandato_inicio: Optional[date] = None
    mandato_fim: Optional[date] = None


class SenadoVotoRaw(BaseModel):
    codigo_senador: int
    voto: Literal["Sim", "Não", "Abstenção", "Ausente", "P-NRV"]


class SenadoVotacaoRaw(BaseModel):
    type: Literal["votacao"] = "votacao"
    codigo_sessao: str
    data: datetime
    descricao: str
    codigo_materia: Optional[str] = None
    resultado: Optional[str] = None
    votos: list[SenadoVotoRaw] = []


class SenadoMateriaRaw(BaseModel):
    type: Literal["materia"] = "materia"
    codigo: str
    tipo: str
    numero: int
    ano: int
    ementa: Optional[str] = None
    situacao: Optional[str] = None
    autor: Optional[str] = None


class SenadoDespesaRaw(BaseModel):
    type: Literal["despesa"] = "despesa"
    codigo_senador: int
    ano: int
    mes: int
    tipo_despesa: str
    valor: Decimal
    cnpj_cpf: Optional[str] = None
    fornecedor: Optional[str] = None
    documento: Optional[str] = None
