"""Senado Federal transformer — raw JSONL to domain schemas."""

from __future__ import annotations

import logging
from typing import Iterator

from models.mandatario import MandatarioCreateSchema
from models.projeto_lei import ProjetoLeiCreateSchema
from models.raw.senado_raw import (
    SenadoMateriaRaw,
    SenadoSenadorRaw,
    SenadoVotacaoRaw,
)

from processing.transformers.base import (
    BaseTransformer,
    MandatarioVotoCreateSchema,
    TransformResult,
    VotacaoCreateSchema,
)

logger = logging.getLogger(__name__)

_HANDLED_TYPES = {"senador", "votacao", "materia"}
_SKIPPED_TYPES = {"despesa"}

# The Senado API uses "P-NRV" (Presente, Não Registrou Voto) which maps
# to Abstenção in our domain model.
_VOTO_MAP = {
    "Sim": "Sim",
    "Não": "Não",
    "Abstenção": "Abstenção",
    "Ausente": "Ausente",
    "P-NRV": "Abstenção",
}


class SenadoTransformer(BaseTransformer):
    """Transform Senado Federal raw records."""

    source_name: str = "senado"

    def transform(self, raw_records: Iterator[dict]) -> TransformResult:
        result = TransformResult()

        for record in raw_records:
            record_type = record.get("type")

            if record_type in _SKIPPED_TYPES:
                continue

            if record_type not in _HANDLED_TYPES:
                logger.debug("senado: unknown record type %r, skipping", record_type)
                continue

            try:
                if record_type == "senador":
                    self._transform_senador(record, result)
                elif record_type == "votacao":
                    self._transform_votacao(record, result)
                elif record_type == "materia":
                    self._transform_materia(record, result)
            except Exception as exc:
                logger.warning("senado: error transforming %s record: %s", record_type, exc)
                result.add_error(record, str(exc), self.source_name)

        logger.info(
            "senado: %d entities, %d relationships, %d errors",
            result.total_entities,
            result.total_relationships,
            len(result.errors),
        )
        return result

    # ------------------------------------------------------------------ #
    # Per-type transformers                                                #
    # ------------------------------------------------------------------ #

    def _transform_senador(self, record: dict, result: TransformResult) -> None:
        raw = SenadoSenadorRaw.model_validate(record)

        mandatario = MandatarioCreateSchema(
            id_tse=str(raw.codigo),
            nome=raw.nome,
            nome_civil=raw.nome_completo,
            cargo="Senador",
            uf=raw.sigla_uf,
            partido_sigla=raw.sigla_partido,
            mandato_inicio=raw.mandato_inicio,
            mandato_fim=raw.mandato_fim,
            # Senado API does not expose CPF.
            cpf_hash=None,
        )
        result.add_entity("mandatarios", mandatario)

    def _transform_votacao(self, record: dict, result: TransformResult) -> None:
        raw = SenadoVotacaoRaw.model_validate(record)

        votacao = VotacaoCreateSchema(
            id_externo=raw.codigo_sessao,
            data=raw.data,
            descricao=raw.descricao,
            resultado=raw.resultado,
        )
        result.add_entity("votacoes", votacao)

        for voto_raw in raw.votos:
            voto_normalizado = _VOTO_MAP.get(voto_raw.voto, voto_raw.voto)
            voto = MandatarioVotoCreateSchema(
                mandatario_id_externo=str(voto_raw.codigo_senador),
                votacao_id_externo=raw.codigo_sessao,
                voto=voto_normalizado,
                data=raw.data,
            )
            result.add_relationship("mandatario_votos", voto)

    def _transform_materia(self, record: dict, result: TransformResult) -> None:
        raw = SenadoMateriaRaw.model_validate(record)

        projeto = ProjetoLeiCreateSchema(
            numero=raw.numero,
            ano=raw.ano,
            tipo=raw.tipo,
            ementa=raw.ementa,
            situacao=raw.situacao,
        )
        result.add_entity("projetos_lei", projeto)
