"""CNJ DataJud transformer — raw JSONL to domain schemas."""

from __future__ import annotations

import logging
from typing import Iterator

from models.processo_judicial import ProcessoJudicialCreateSchema
from models.raw.cnj_raw import CnjProcessoRaw
from pii import hash_cpf_or_cnpj

from processing.transformers.base import BaseTransformer, TransformResult

logger = logging.getLogger(__name__)

_HANDLED_TYPES = {"processo"}


class CnjTransformer(BaseTransformer):
    """Transform CNJ DataJud raw records."""

    source_name: str = "cnj"

    def transform(self, raw_records: Iterator[dict]) -> TransformResult:
        result = TransformResult()

        for record in raw_records:
            record_type = record.get("type")

            if record_type not in _HANDLED_TYPES:
                logger.debug("cnj: unknown record type %r, skipping", record_type)
                continue

            try:
                self._transform_processo(record, result)
            except Exception as exc:
                logger.warning("cnj: error transforming processo record: %s", exc)
                result.add_error(record, str(exc), self.source_name)

        logger.info(
            "cnj: %d entities, %d relationships, %d errors",
            result.total_entities,
            result.total_relationships,
            len(result.errors),
        )
        return result

    # ------------------------------------------------------------------ #
    # Per-type transformers                                                #
    # ------------------------------------------------------------------ #

    def _transform_processo(self, record: dict, result: TransformResult) -> None:
        raw = CnjProcessoRaw.model_validate(record)

        processo = ProcessoJudicialCreateSchema(
            numero_cnj=raw.numero_cnj,
            tipo=raw.classe,
            tribunal=raw.tribunal,
            situacao=raw.situacao,
            valor_causa=raw.valor_causa,
        )
        result.add_entity("processos_judiciais", processo)

        # Hash party CPFs/CNPJs for entity linking.
        for parte in raw.partes:
            if not parte.cpf_cnpj:
                continue
            try:
                parte_hash = hash_cpf_or_cnpj(parte.cpf_cnpj)
            except ValueError:
                logger.warning(
                    "cnj: invalid CPF/CNPJ %r for parte %s in processo %s",
                    parte.cpf_cnpj,
                    parte.nome,
                    raw.numero_cnj,
                )
                continue

            parte_rel = {
                "processo_numero_cnj": raw.numero_cnj,
                "nome": parte.nome,
                "cpf_cnpj_hash": parte_hash,
                "tipo_parte": parte.tipo,
            }
            result.add_relationship("processo_partes", parte_rel)
