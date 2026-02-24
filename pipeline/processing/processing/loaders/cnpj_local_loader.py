"""CnpjLocalLoader — load CNPJ data into local DuckDB or SQLite for fast queries."""

from __future__ import annotations

import logging
import sqlite3
from typing import Any, Literal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DDL shared between both engines (standard SQL subset)
# ---------------------------------------------------------------------------

_DDL_EMPRESAS = """
CREATE TABLE IF NOT EXISTS empresas (
    cnpj_basico       TEXT PRIMARY KEY,
    razao_social      TEXT NOT NULL,
    natureza_juridica TEXT,
    qualificacao_resp TEXT,
    capital_social    DECIMAL(18,2),
    porte             TEXT
)
"""

_DDL_SOCIOS = """
CREATE TABLE IF NOT EXISTS socios (
    cnpj_basico        TEXT NOT NULL,
    tipo_socio         INTEGER,
    nome_socio         TEXT NOT NULL,
    cpf_cnpj_socio     TEXT,
    qualificacao       TEXT,
    data_entrada       DATE,
    percentual_capital DECIMAL(6,2),
    representante_legal TEXT,
    PRIMARY KEY (cnpj_basico, nome_socio, tipo_socio)
)
"""

_DDL_ESTABELECIMENTOS = """
CREATE TABLE IF NOT EXISTS estabelecimentos (
    cnpj_basico        TEXT NOT NULL,
    cnpj_ordem         TEXT NOT NULL,
    cnpj_dv            TEXT NOT NULL,
    situacao_cadastral TEXT,
    data_situacao      DATE,
    cnae_principal     TEXT,
    cnaes_secundarios  TEXT,
    logradouro         TEXT,
    municipio          TEXT,
    uf                 TEXT,
    cep                TEXT,
    PRIMARY KEY (cnpj_basico, cnpj_ordem, cnpj_dv)
)
"""

_ALL_DDL = [_DDL_EMPRESAS, _DDL_SOCIOS, _DDL_ESTABELECIMENTOS]


class CnpjLocalLoader:
    """Load CNPJ data into local DuckDB or SQLite for fast local queries.

    DuckDB is the default engine because of its superior analytical
    performance, but SQLite is supported as a lightweight fallback.
    """

    def __init__(
        self,
        db_path: str,
        engine: Literal["duckdb", "sqlite"] = "duckdb",
    ) -> None:
        """
        Args:
            db_path: Path to the local database file.
            engine: ``"duckdb"`` (default) or ``"sqlite"``.
        """
        self._engine_name = engine
        self._db_path = db_path

        if engine == "duckdb":
            import duckdb

            self._conn = duckdb.connect(db_path)
        elif engine == "sqlite":
            self._conn = sqlite3.connect(db_path)
        else:
            raise ValueError(f"Unsupported engine: {engine!r}. Use 'duckdb' or 'sqlite'.")

        logger.info("CnpjLocalLoader initialised (engine=%s, path=%s)", engine, db_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_tables(self) -> None:
        """Create ``empresas``, ``socios``, ``estabelecimentos`` tables if they
        do not already exist."""
        for ddl in _ALL_DDL:
            self._conn.execute(ddl)
        if self._engine_name == "sqlite":
            self._conn.commit()
        logger.info("CNPJ tables ensured")

    def load_empresas(self, records: list[dict[str, Any]]) -> int:
        """Batch insert/replace empresas.

        Returns:
            Number of records loaded.
        """
        return self._upsert(
            table="empresas",
            columns=[
                "cnpj_basico", "razao_social", "natureza_juridica",
                "qualificacao_resp", "capital_social", "porte",
            ],
            records=records,
        )

    def load_socios(self, records: list[dict[str, Any]]) -> int:
        """Batch insert/replace socios.

        Returns:
            Number of records loaded.
        """
        return self._upsert(
            table="socios",
            columns=[
                "cnpj_basico", "tipo_socio", "nome_socio", "cpf_cnpj_socio",
                "qualificacao", "data_entrada", "percentual_capital",
                "representante_legal",
            ],
            records=records,
        )

    def load_estabelecimentos(self, records: list[dict[str, Any]]) -> int:
        """Batch insert/replace estabelecimentos.

        Returns:
            Number of records loaded.
        """
        return self._upsert(
            table="estabelecimentos",
            columns=[
                "cnpj_basico", "cnpj_ordem", "cnpj_dv", "situacao_cadastral",
                "data_situacao", "cnae_principal", "cnaes_secundarios",
                "logradouro", "municipio", "uf", "cep",
            ],
            records=records,
        )

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
        logger.info("CnpjLocalLoader connection closed (%s)", self._engine_name)

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> CnpjLocalLoader:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _upsert(
        self,
        table: str,
        columns: list[str],
        records: list[dict[str, Any]],
    ) -> int:
        """INSERT OR REPLACE rows in batches within a single transaction.

        Both DuckDB and SQLite support ``INSERT OR REPLACE INTO``.
        """
        if not records:
            return 0

        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join(columns)
        stmt = f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})"

        rows = [
            tuple(record.get(col) for col in columns)
            for record in records
        ]

        if self._engine_name == "duckdb":
            self._conn.executemany(stmt, rows)
        else:
            # SQLite — wrap in explicit transaction for performance
            self._conn.execute("BEGIN")
            try:
                self._conn.executemany(stmt, rows)
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

        loaded = len(rows)
        logger.info("Loaded %d records into %s", loaded, table)
        return loaded
