"""Raw JSONL models for Portal Transparencia / CGU spider output."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, field_validator

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

    @field_validator("tipo_sancao", mode="before")
    @classmethod
    def _extract_tipo_sancao(cls, v: object) -> str:
        """API returns a dict like {"descricaoResumida": "..."}."""
        if isinstance(v, dict):
            return v.get("descricaoResumida") or v.get("descricaoPortal") or str(v)
        return str(v)

    @field_validator("data_inicio", "data_fim", mode="before")
    @classmethod
    def _parse_br_date(cls, v: object) -> date | None:
        """Accept DD/MM/YYYY in addition to ISO format."""
        if v is None or v == "":
            return None
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            if "/" in v:
                try:
                    return datetime.strptime(v, "%d/%m/%Y").date()
                except ValueError:
                    return None  # unparseable date
            if v.lower().startswith("sem "):
                return None  # "Sem informação"
        return v  # let Pydantic handle ISO strings


class TransparenciaCartaoCorporativoRaw(BaseModel):
    type: Literal["cartao_corporativo"] = "cartao_corporativo"
    cpf_portador: str
    nome_portador: str
    valor: Decimal
    data: date
    estabelecimento: Optional[str] = None
    cnpj_estabelecimento: Optional[str] = None
