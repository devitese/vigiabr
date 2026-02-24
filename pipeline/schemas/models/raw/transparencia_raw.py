"""Raw JSONL models for Portal Transparencia / CGU spider output."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel

__all__ = [
    "TransparenciaEmendaRaw",
    "TransparenciaContratoRaw",
    "TransparenciaCeisRaw",
    "TransparenciaCartaoCorporativoRaw",
]


class TransparenciaEmendaRaw(BaseModel):
    type: Literal["emenda"] = "emenda"
    numero: str
    autor: str
    tipo: Optional[str] = None
    ano: int
    valor_empenhado: Optional[Decimal] = None
    valor_pago: Decimal
    funcao: Optional[str] = None
    subfuncao: Optional[str] = None
    beneficiario_nome: Optional[str] = None
    beneficiario_cnpj_cpf: Optional[str] = None
    localidade: Optional[str] = None


class TransparenciaContratoRaw(BaseModel):
    type: Literal["contrato"] = "contrato"
    numero: str
    orgao: str
    objeto: Optional[str] = None
    valor: Decimal
    data_assinatura: date
    data_fim_vigencia: Optional[date] = None
    cnpj_contratado: Optional[str] = None
    nome_contratado: Optional[str] = None
    modalidade_licitacao: Optional[str] = None


class TransparenciaCeisRaw(BaseModel):
    type: Literal["ceis"] = "ceis"
    cnpj_cpf: str
    nome: str
    tipo_sancao: str
    orgao_sancionador: Optional[str] = None
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None


class TransparenciaCartaoCorporativoRaw(BaseModel):
    type: Literal["cartao_corporativo"] = "cartao_corporativo"
    cpf_portador: str
    nome_portador: str
    valor: Decimal
    data: date
    estabelecimento: Optional[str] = None
    cnpj_estabelecimento: Optional[str] = None
