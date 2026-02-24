"""Querido Diario (OKBR) transformer — raw JSONL to domain schemas."""

from __future__ import annotations

import logging
from typing import Iterator

from models.pessoa_fisica import PessoaFisicaCreateSchema, TipoPessoa
from models.raw.querido_diario_raw import QueridoDiarioNomeacaoRaw
from pii import hash_cpf

from processing.transformers.base import (
    BaseTransformer,
    MandatarioContratacaoCreateSchema,
    TransformResult,
)

logger = logging.getLogger(__name__)

_HANDLED_TYPES = {"nomeacao"}
# Publicacao needs NLP (Phase 2) — skip for MVP.
_SKIPPED_TYPES = {"publicacao"}


class QueridoDiarioTransformer(BaseTransformer):
    """Transform Querido Diario (official gazette) raw records."""

    source_name: str = "querido_diario"

    def transform(self, raw_records: Iterator[dict]) -> TransformResult:
        result = TransformResult()

        for record in raw_records:
            record_type = record.get("type")

            if record_type in _SKIPPED_TYPES:
                continue

            if record_type not in _HANDLED_TYPES:
                logger.debug("querido_diario: unknown record type %r, skipping", record_type)
                continue

            try:
                if record_type == "nomeacao":
                    self._transform_nomeacao(record, result)
            except Exception as exc:
                logger.warning(
                    "querido_diario: error transforming %s record: %s", record_type, exc
                )
                result.add_error(record, str(exc), self.source_name)

        logger.info(
            "querido_diario: %d entities, %d relationships, %d errors",
            result.total_entities,
            result.total_relationships,
            len(result.errors),
        )
        return result

    # ------------------------------------------------------------------ #
    # Per-type transformers                                                #
    # ------------------------------------------------------------------ #

    def _transform_nomeacao(self, record: dict, result: TransformResult) -> None:
        raw = QueridoDiarioNomeacaoRaw.model_validate(record)

        # CPF is optional in gazette data.  If absent, we cannot create a
        # PessoaFisica (cpf_hash is required), so we skip the entity but
        # still log for visibility.
        if not raw.cpf:
            logger.debug(
                "querido_diario: nomeacao without CPF for %s, skipping entity creation",
                raw.nome,
            )
            return

        cpf_hash = hash_cpf(raw.cpf)

        # Determine person type from appointment kind.
        tipo = TipoPessoa.ASSESSOR if raw.tipo in ("DAS", "Nomeacao") else TipoPessoa.OUTRO

        pessoa = PessoaFisicaCreateSchema(
            nome=raw.nome,
            cpf_hash=cpf_hash,
            tipo=tipo,
        )
        result.add_entity("pessoas_fisicas", pessoa)

        # Emit contratacao relationship for loader to resolve mandatario link.
        contratacao = MandatarioContratacaoCreateSchema(
            pessoa_cpf_hash=cpf_hash,
            pessoa_nome=raw.nome,
            cargo=raw.cargo,
            orgao=raw.orgao,
            data_publicacao=raw.data_publicacao,
        )
        result.add_relationship("mandatario_contratacoes", contratacao)
