"""Raw JSONL models for Receita Federal CNPJ dump output."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel

__all__ = [
    "CnpjEmpresaRaw",
    "CnpjSocioRaw",
    "CnpjEstabelecimentoRaw",
]


class CnpjEmpresaRaw(BaseModel):
    type: Literal["empresa"] = "empresa"
    cnpj_basico: str
    razao_social: str
    natureza_juridica: str
    qualificacao_responsavel: Optional[str] = None
    capital_social: Optional[Decimal] = None
    porte: Optional[Literal["ME", "EPP", "DEMAIS", "NAO_INFORMADO"]] = None


class CnpjSocioRaw(BaseModel):
    type: Literal["socio"] = "socio"
    cnpj_basico: str
    tipo_socio: Literal[1, 2, 3]
    nome_socio: str
    cpf_cnpj_socio: Optional[str] = None
    qualificacao: Optional[str] = None
    data_entrada: Optional[date] = None
    percentual_capital: Optional[Decimal] = None
    representante_legal: Optional[str] = None


class CnpjEstabelecimentoRaw(BaseModel):
    type: Literal["estabelecimento"] = "estabelecimento"
    cnpj_basico: str
    cnpj_ordem: str
    cnpj_dv: str
    situacao_cadastral: Optional[str] = None
    data_situacao: Optional[date] = None
    cnae_principal: Optional[str] = None
    cnaes_secundarios: list[str] = []
    logradouro: Optional[str] = None
    municipio: Optional[str] = None
    uf: Optional[str] = None
    cep: Optional[str] = None
