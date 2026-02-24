"""Portal Transparencia / CGU transformer — raw JSONL to domain schemas."""

from __future__ import annotations

import logging
from typing import Iterator

from models.contrato_gov import ContratoGovCreateSchema
from models.emenda import EmendaCreateSchema
from models.raw.transparencia_raw import (
    TransparenciaCeisRaw,
    TransparenciaContratoRaw,
    TransparenciaEmendaRaw,
)
from pii import hash_cpf_or_cnpj

from processing.transformers.base import (
    BaseTransformer,
    CeisFlagSchema,
    TransformResult,
)

logger = logging.getLogger(__name__)

_HANDLED_TYPES = {"emenda", "contrato", "ceis"}
_SKIPPED_TYPES = {"cartao_corporativo"}


class TransparenciaTransformer(BaseTransformer):
    """Transform Portal Transparencia / CGU raw records."""

    source_name: str = "transparencia"

    def transform(self, raw_records: Iterator[dict]) -> TransformResult:
        result = TransformResult()

        for record in raw_records:
            record_type = record.get("type")

            if record_type in _SKIPPED_TYPES:
                continue

            if record_type not in _HANDLED_TYPES:
                logger.debug("transparencia: unknown record type %r, skipping", record_type)
                continue

            try:
                if record_type == "emenda":
                    self._transform_emenda(record, result)
                elif record_type == "contrato":
                    self._transform_contrato(record, result)
                elif record_type == "ceis":
                    self._transform_ceis(record, result)
            except Exception as exc:
                logger.warning(
                    "transparencia: error transforming %s record: %s", record_type, exc
                )
                result.add_error(record, str(exc), self.source_name)

        logger.info(
            "transparencia: %d entities, %d relationships, %d errors",
            result.total_entities,
            result.total_relationships,
            len(result.errors),
        )
        return result

    # ------------------------------------------------------------------ #
    # Per-type transformers                                                #
    # ------------------------------------------------------------------ #

    def _transform_emenda(self, record: dict, result: TransformResult) -> None:
        raw = TransparenciaEmendaRaw.model_validate(record)

        emenda = EmendaCreateSchema(
            numero=raw.numero,
            tipo=raw.tipo,
            valor_pago=raw.valor_pago,
            ano=raw.ano,
            funcao=raw.funcao,
            # autor_id (UUID) is resolved at load time by matching
            # ``raw.autor`` against mandatario names.
        )
        result.add_entity("emendas", emenda)

        # Hash beneficiario CPF/CNPJ if present (for entity linking).
        if raw.beneficiario_cnpj_cpf:
            try:
                hash_cpf_or_cnpj(raw.beneficiario_cnpj_cpf)
            except ValueError:
                logger.warning(
                    "transparencia: invalid beneficiario CPF/CNPJ %r in emenda %s",
                    raw.beneficiario_cnpj_cpf,
                    raw.numero,
                )

    def _transform_contrato(self, record: dict, result: TransformResult) -> None:
        raw = TransparenciaContratoRaw.model_validate(record)

        contrato = ContratoGovCreateSchema(
            numero=raw.numero,
            objeto=raw.objeto,
            valor=raw.valor,
            orgao_contratante=raw.orgao,
            data_assinatura=raw.data_assinatura,
            # empresa_id (UUID) is resolved at load time by CNPJ lookup.
        )
        result.add_entity("contratos_gov", contrato)

        # Hash contracted company CNPJ for entity linking.
        if raw.cnpj_contratado:
            try:
                hash_cpf_or_cnpj(raw.cnpj_contratado)
            except ValueError:
                logger.warning(
                    "transparencia: invalid CNPJ %r in contrato %s",
                    raw.cnpj_contratado,
                    raw.numero,
                )

    def _transform_ceis(self, record: dict, result: TransformResult) -> None:
        raw = TransparenciaCeisRaw.model_validate(record)

        try:
            cpf_cnpj_hash = hash_cpf_or_cnpj(raw.cnpj_cpf)
        except ValueError:
            logger.warning(
                "transparencia: invalid CPF/CNPJ %r in CEIS record for %s",
                raw.cnpj_cpf,
                raw.nome,
            )
            result.add_error(record, f"Invalid CPF/CNPJ: {raw.cnpj_cpf!r}", self.source_name)
            return

        flag = CeisFlagSchema(
            cpf_cnpj_hash=cpf_cnpj_hash,
            nome=raw.nome,
            tipo_sancao=raw.tipo_sancao,
            orgao_sancionador=raw.orgao_sancionador,
            data_inicio=raw.data_inicio,
            data_fim=raw.data_fim,
        )
        # CEIS entries are flags for entity linking, not standalone entities.
        result.add_relationship("ceis_flags", flag)
