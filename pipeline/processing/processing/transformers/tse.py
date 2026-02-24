"""TSE (election data) transformer — raw JSONL to domain schemas."""

from __future__ import annotations

import logging
from typing import Iterator

from models.mandatario import MandatarioCreateSchema
from models.partido import PartidoCreateSchema
from models.raw.tse_raw import (
    TseBemDeclaradoRaw,
    TseCandidatoRaw,
    TseDoacaoRaw,
)
from pii import hash_cpf, hash_cpf_or_cnpj

from processing.transformers.base import (
    BaseTransformer,
    BemDeclaradoPendingSchema,
    DoacaoCreateSchema,
    TransformResult,
)

logger = logging.getLogger(__name__)

_HANDLED_TYPES = {"candidato", "bem_declarado", "doacao"}
_SKIPPED_TYPES = {"despesa_campanha"}


class TseTransformer(BaseTransformer):
    """Transform TSE election data raw records."""

    source_name: str = "tse"

    def transform(self, raw_records: Iterator[dict]) -> TransformResult:
        result = TransformResult()

        for record in raw_records:
            record_type = record.get("type")

            if record_type in _SKIPPED_TYPES:
                continue

            if record_type not in _HANDLED_TYPES:
                logger.debug("tse: unknown record type %r, skipping", record_type)
                continue

            try:
                if record_type == "candidato":
                    self._transform_candidato(record, result)
                elif record_type == "bem_declarado":
                    self._transform_bem_declarado(record, result)
                elif record_type == "doacao":
                    self._transform_doacao(record, result)
            except Exception as exc:
                logger.warning("tse: error transforming %s record: %s", record_type, exc)
                result.add_error(record, str(exc), self.source_name)

        logger.info(
            "tse: %d entities, %d relationships, %d errors",
            result.total_entities,
            result.total_relationships,
            len(result.errors),
        )
        return result

    # ------------------------------------------------------------------ #
    # Per-type transformers                                                #
    # ------------------------------------------------------------------ #

    def _transform_candidato(self, record: dict, result: TransformResult) -> None:
        raw = TseCandidatoRaw.model_validate(record)

        cpf_hash = hash_cpf(raw.cpf)

        # Create/upsert mandatario linked by CPF hash.
        mandatario = MandatarioCreateSchema(
            id_tse=raw.sequencial,
            nome=raw.nome,
            cargo=raw.cargo,
            uf=raw.sigla_uf,
            partido_sigla=raw.sigla_partido,
            cpf_hash=cpf_hash,
        )
        result.add_entity("mandatarios", mandatario)

        # Emit partido for upsert if present.
        if raw.sigla_partido:
            partido = PartidoCreateSchema(
                sigla=raw.sigla_partido,
                nome=raw.sigla_partido,  # Full name not in TSE raw; use sigla.
            )
            result.add_entity("partidos", partido)

    def _transform_bem_declarado(self, record: dict, result: TransformResult) -> None:
        raw = TseBemDeclaradoRaw.model_validate(record)

        # mandatario_id (UUID) is resolved at load time via sequencial lookup.
        bem = BemDeclaradoPendingSchema(
            mandatario_id_externo=raw.sequencial_candidato,
            tipo=raw.tipo_bem,
            descricao=raw.descricao,
            valor_declarado=raw.valor,
            ano_eleicao=raw.ano_eleicao,
        )
        result.add_entity("bens_patrimoniais", bem)

    def _transform_doacao(self, record: dict, result: TransformResult) -> None:
        raw = TseDoacaoRaw.model_validate(record)

        doador_hash: str | None = None
        if raw.cpf_cnpj_doador:
            try:
                doador_hash = hash_cpf_or_cnpj(raw.cpf_cnpj_doador)
            except ValueError:
                logger.warning(
                    "tse: invalid CPF/CNPJ for doador %r, skipping hash",
                    raw.cpf_cnpj_doador,
                )

        doacao = DoacaoCreateSchema(
            mandatario_id_externo=raw.sequencial_candidato,
            valor=raw.valor,
            data=raw.data_receita,
            eleicao_ano=raw.ano_eleicao,
            origem=raw.tipo_doador,
            doador_nome=raw.nome_doador,
            doador_cpf_cnpj_hash=doador_hash,
        )
        result.add_relationship("doacoes", doacao)
