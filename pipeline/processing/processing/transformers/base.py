"""Base transformer — abstract class and shared data structures."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterator, Optional

from models.base import BaseSchema

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------- #
# Intermediate schemas for records whose DB UUIDs are resolved at load  #
# time.  These use external (source) IDs instead.                       #
# -------------------------------------------------------------------- #


class VotacaoCreateSchema(BaseSchema):
    """Votacao ready for insertion (no DB id/timestamps yet)."""

    id_externo: str
    data: datetime
    descricao: Optional[str] = None
    tipo_proposicao: Optional[str] = None
    resultado: Optional[str] = None


class MandatarioVotoCreateSchema(BaseSchema):
    """Individual vote record keyed by external IDs.

    The loader resolves ``mandatario_id_externo`` and
    ``votacao_id_externo`` to database UUIDs before inserting.
    """

    mandatario_id_externo: str
    votacao_id_externo: str
    voto: str
    data: Optional[datetime] = None


class DoacaoCreateSchema(BaseSchema):
    """Donation record keyed by candidate external ID.

    ``mandatario_id_externo`` is resolved to a UUID by the loader.
    """

    mandatario_id_externo: str
    valor: Decimal
    data: Optional[date] = None
    eleicao_ano: Optional[int] = None
    origem: Optional[str] = None
    doador_nome: Optional[str] = None
    doador_cpf_cnpj_hash: Optional[str] = None


class BemDeclaradoPendingSchema(BaseSchema):
    """Asset declaration keyed by candidate external ID.

    ``mandatario_id_externo`` is resolved to a UUID by the loader, then
    inserted as a ``BemPatrimonialCreateSchema``.
    """

    mandatario_id_externo: str
    tipo: str
    descricao: Optional[str] = None
    valor_declarado: Decimal
    ano_eleicao: int


class CeisFlagSchema(BaseSchema):
    """Lightweight flag for CEIS (sanctions) entity linking."""

    cpf_cnpj_hash: str
    nome: str
    tipo_sancao: str
    orgao_sancionador: Optional[str] = None
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None


class MandatarioContratacaoCreateSchema(BaseSchema):
    """Appointment/hiring record from Querido Diario.

    Uses ``pessoa_cpf_hash`` for linking.  The loader performs entity
    resolution against the mandatario table.
    """

    pessoa_cpf_hash: str
    pessoa_nome: str
    cargo: str
    orgao: Optional[str] = None
    data_publicacao: Optional[date] = None


# -------------------------------------------------------------------- #
# Error / result data-classes                                           #
# -------------------------------------------------------------------- #


@dataclass
class TransformError:
    """A single record that failed transformation."""

    record: dict
    error: str
    source: str


@dataclass
class TransformResult:
    """Holds categorized domain objects ready for loading.

    - entities:      table_name -> list of Pydantic create schemas
    - relationships: relationship_name -> list of relationship schemas
    - errors:        records that failed transformation
    """

    entities: dict[str, list] = field(default_factory=dict)
    relationships: dict[str, list] = field(default_factory=dict)
    errors: list[TransformError] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # Convenience helpers                                                  #
    # ------------------------------------------------------------------ #

    def add_entity(self, table: str, obj: object) -> None:
        self.entities.setdefault(table, []).append(obj)

    def add_relationship(self, name: str, obj: object) -> None:
        self.relationships.setdefault(name, []).append(obj)

    def add_error(self, record: dict, error: str, source: str) -> None:
        self.errors.append(TransformError(record=record, error=error, source=source))

    @property
    def total_entities(self) -> int:
        return sum(len(v) for v in self.entities.values())

    @property
    def total_relationships(self) -> int:
        return sum(len(v) for v in self.relationships.values())


class BaseTransformer(ABC):
    """Abstract base for all source transformers."""

    source_name: str  # e.g. "camara", "senado"

    # ------------------------------------------------------------------ #
    # I/O helpers                                                          #
    # ------------------------------------------------------------------ #

    def read_jsonl(self, path: Path) -> Iterator[dict]:
        """Read a JSONL file line-by-line, yielding parsed dicts.

        Malformed lines are logged and skipped.
        """
        with path.open("r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    logger.warning(
                        "%s:%d — invalid JSON, skipping: %s", path.name, lineno, exc
                    )

    def find_latest_run(self, base_dir: Path) -> Path | None:
        """Return the most recent YYYY-MM-DD directory under
        ``base_dir/data/raw/{source_name}/``, or ``None`` if none exist.
        """
        source_dir = base_dir / "data" / "raw" / self.source_name
        if not source_dir.is_dir():
            logger.warning("Source directory does not exist: %s", source_dir)
            return None

        date_dirs = sorted(
            (d for d in source_dir.iterdir() if d.is_dir()),
            key=lambda d: d.name,
            reverse=True,
        )
        if not date_dirs:
            logger.warning("No run directories found under %s", source_dir)
            return None

        return date_dirs[0]

    # ------------------------------------------------------------------ #
    # Abstract interface                                                   #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def transform(self, raw_records: Iterator[dict]) -> TransformResult:
        """Transform raw records into domain objects.

        Implementations must be resilient: catch per-record errors, log them,
        and continue processing the remaining records.
        """
