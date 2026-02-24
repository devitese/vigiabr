"""Receita Federal CNPJ dump transformer — raw JSONL to domain schemas."""

from __future__ import annotations

import logging
from typing import Iterator

from models.empresa import EmpresaCreateSchema
from models.pessoa_fisica import PessoaFisicaCreateSchema, TipoPessoa
from models.raw.cnpj_raw import (
    CnpjEmpresaRaw,
    CnpjEstabelecimentoRaw,
    CnpjSocioRaw,
)
from pii import hash_cpf_or_cnpj

from processing.transformers.base import BaseTransformer, TransformResult

logger = logging.getLogger(__name__)

_HANDLED_TYPES = {"empresa", "socio", "estabelecimento"}


class CnpjTransformer(BaseTransformer):
    """Transform Receita Federal CNPJ dump records."""

    source_name: str = "cnpj"

    def transform(self, raw_records: Iterator[dict]) -> TransformResult:
        result = TransformResult()

        for record in raw_records:
            record_type = record.get("type")

            if record_type not in _HANDLED_TYPES:
                logger.debug("cnpj: unknown record type %r, skipping", record_type)
                continue

            try:
                if record_type == "empresa":
                    self._transform_empresa(record, result)
                elif record_type == "socio":
                    self._transform_socio(record, result)
                elif record_type == "estabelecimento":
                    self._transform_estabelecimento(record, result)
            except Exception as exc:
                logger.warning("cnpj: error transforming %s record: %s", record_type, exc)
                result.add_error(record, str(exc), self.source_name)

        logger.info(
            "cnpj: %d entities, %d relationships, %d errors",
            result.total_entities,
            result.total_relationships,
            len(result.errors),
        )
        return result

    # ------------------------------------------------------------------ #
    # Per-type transformers                                                #
    # ------------------------------------------------------------------ #

    def _transform_empresa(self, record: dict, result: TransformResult) -> None:
        raw = CnpjEmpresaRaw.model_validate(record)

        empresa = EmpresaCreateSchema(
            cnpj=raw.cnpj_basico,
            razao_social=raw.razao_social,
            capital_social=raw.capital_social,
        )
        result.add_entity("empresas", empresa)

    def _transform_socio(self, record: dict, result: TransformResult) -> None:
        raw = CnpjSocioRaw.model_validate(record)

        # tipo_socio: 1 = PJ, 2 = PF, 3 = Estrangeiro
        if raw.tipo_socio == 2 and raw.cpf_cnpj_socio:
            # Pessoa Fisica socio — hash CPF.
            try:
                cpf_hash = hash_cpf_or_cnpj(raw.cpf_cnpj_socio)
            except ValueError:
                logger.warning(
                    "cnpj: invalid CPF %r for socio %s, skipping",
                    raw.cpf_cnpj_socio,
                    raw.nome_socio,
                )
                result.add_error(
                    record, f"Invalid CPF: {raw.cpf_cnpj_socio!r}", self.source_name
                )
                return

            pessoa = PessoaFisicaCreateSchema(
                nome=raw.nome_socio,
                cpf_hash=cpf_hash,
                tipo=TipoPessoa.SOCIO,
            )
            result.add_entity("pessoas_fisicas", pessoa)

            # Emit relationship: pessoa_fisica -> empresa (SOCIO_DE).
            socio_rel = {
                "pessoa_cpf_hash": cpf_hash,
                "empresa_cnpj": raw.cnpj_basico,
                "qualificacao": raw.qualificacao,
                "data_entrada": raw.data_entrada.isoformat() if raw.data_entrada else None,
                "percentual_capital": str(raw.percentual_capital) if raw.percentual_capital else None,
            }
            result.add_relationship("pessoa_empresa_socios", socio_rel)

        elif raw.tipo_socio == 1 and raw.cpf_cnpj_socio:
            # PJ socio — hash CNPJ for entity linking.
            try:
                cnpj_hash = hash_cpf_or_cnpj(raw.cpf_cnpj_socio)
            except ValueError:
                logger.warning(
                    "cnpj: invalid CNPJ %r for socio PJ %s, skipping",
                    raw.cpf_cnpj_socio,
                    raw.nome_socio,
                )
                return

            socio_rel = {
                "socio_cnpj_hash": cnpj_hash,
                "empresa_cnpj": raw.cnpj_basico,
                "qualificacao": raw.qualificacao,
                "data_entrada": raw.data_entrada.isoformat() if raw.data_entrada else None,
            }
            result.add_relationship("pessoa_empresa_socios", socio_rel)

    def _transform_estabelecimento(self, record: dict, result: TransformResult) -> None:
        """Enrich an existing empresa with CNAE and location data.

        The full CNPJ is reconstructed from basico + ordem + dv.
        """
        raw = CnpjEstabelecimentoRaw.model_validate(record)

        cnpj_completo = f"{raw.cnpj_basico}{raw.cnpj_ordem}{raw.cnpj_dv}"

        # Stored as an enrichment record — the loader merges into the
        # matching empresa row.
        enrichment = {
            "cnpj_basico": raw.cnpj_basico,
            "cnpj_completo": cnpj_completo,
            "cnae": raw.cnae_principal,
            "situacao": raw.situacao_cadastral,
            "municipio": raw.municipio,
            "uf": raw.uf,
        }
        result.add_relationship("empresa_enrichments", enrichment)
