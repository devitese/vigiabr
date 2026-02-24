"""Camara dos Deputados transformer — raw JSONL to domain schemas."""

from __future__ import annotations

import logging
from typing import Iterator

from models.mandatario import MandatarioCreateSchema
from models.projeto_lei import ProjetoLeiCreateSchema
from models.raw.camara_raw import (
    CamaraDeputadoRaw,
    CamaraProposicaoRaw,
    CamaraVotacaoRaw,
)
from pii import hash_cpf

from processing.transformers.base import (
    BaseTransformer,
    MandatarioVotoCreateSchema,
    TransformResult,
    VotacaoCreateSchema,
)

logger = logging.getLogger(__name__)

# Raw types handled in this transformer.
_HANDLED_TYPES = {"deputado", "votacao", "proposicao"}
# Types deliberately skipped for MVP.
_SKIPPED_TYPES = {"despesa", "frente"}


class CamaraTransformer(BaseTransformer):
    """Transform Camara dos Deputados raw records."""

    source_name: str = "camara"

    def transform(self, raw_records: Iterator[dict]) -> TransformResult:
        result = TransformResult()

        for record in raw_records:
            record_type = record.get("type")

            if record_type in _SKIPPED_TYPES:
                continue

            if record_type not in _HANDLED_TYPES:
                logger.debug("camara: unknown record type %r, skipping", record_type)
                continue

            try:
                if record_type == "deputado":
                    self._transform_deputado(record, result)
                elif record_type == "votacao":
                    self._transform_votacao(record, result)
                elif record_type == "proposicao":
                    self._transform_proposicao(record, result)
            except Exception as exc:
                logger.warning("camara: error transforming %s record: %s", record_type, exc)
                result.add_error(record, str(exc), self.source_name)

        logger.info(
            "camara: %d entities, %d relationships, %d errors",
            result.total_entities,
            result.total_relationships,
            len(result.errors),
        )
        return result

    # ------------------------------------------------------------------ #
    # Per-type transformers                                                #
    # ------------------------------------------------------------------ #

    def _transform_deputado(self, record: dict, result: TransformResult) -> None:
        raw = CamaraDeputadoRaw.model_validate(record)

        cpf_hash: str | None = None
        if raw.cpf:
            cpf_hash = hash_cpf(raw.cpf)

        mandatario = MandatarioCreateSchema(
            id_tse=str(raw.id),
            nome=raw.nome,
            nome_civil=raw.nome_civil,
            cargo="Deputado Federal",
            uf=raw.sigla_uf,
            partido_sigla=raw.sigla_partido,
            cpf_hash=cpf_hash,
        )
        result.add_entity("mandatarios", mandatario)

    def _transform_votacao(self, record: dict, result: TransformResult) -> None:
        raw = CamaraVotacaoRaw.model_validate(record)

        votacao = VotacaoCreateSchema(
            id_externo=raw.id_votacao,
            data=raw.data,
            descricao=raw.descricao,
        )
        result.add_entity("votacoes", votacao)

        for voto_raw in raw.votos:
            voto = MandatarioVotoCreateSchema(
                mandatario_id_externo=str(voto_raw.id_deputado),
                votacao_id_externo=raw.id_votacao,
                voto=voto_raw.voto,
                data=raw.data,
            )
            result.add_relationship("mandatario_votos", voto)

    def _transform_proposicao(self, record: dict, result: TransformResult) -> None:
        raw = CamaraProposicaoRaw.model_validate(record)

        projeto = ProjetoLeiCreateSchema(
            numero=raw.numero,
            ano=raw.ano,
            tipo=raw.tipo,
            ementa=raw.ementa,
            tema=raw.tema,
            situacao=raw.situacao,
        )
        result.add_entity("projetos_lei", projeto)
