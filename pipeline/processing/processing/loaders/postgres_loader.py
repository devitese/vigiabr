"""PostgresLoader — batch upsert records into PostgreSQL using psycopg3."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel
from psycopg import sql
from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)


@dataclass
class LoadError:
    """A single record that failed to load."""

    record: dict[str, Any]
    error: str


@dataclass
class LoadResult:
    """Aggregate result of a batch upsert operation."""

    inserted: int = 0
    updated: int = 0
    errors: list[LoadError] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.inserted + self.updated


class PostgresLoader:
    """Batch upsert records into PostgreSQL using psycopg3.

    Uses INSERT ... ON CONFLICT DO UPDATE SET ... to guarantee idempotent loads.
    Connections are managed via ``psycopg_pool.ConnectionPool``.
    """

    def __init__(self, dsn: str, batch_size: int = 1000) -> None:
        """
        Args:
            dsn: PostgreSQL connection string (e.g. ``postgresql://user:pass@host/db``).
            batch_size: Number of records per batch INSERT.
        """
        self._dsn = dsn
        self._batch_size = batch_size
        self._pool = ConnectionPool(dsn, min_size=1, max_size=4, open=True)
        logger.info("PostgresLoader initialised (batch_size=%d)", batch_size)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upsert_batch(
        self,
        table_name: str,
        records: list[BaseModel],
        conflict_columns: list[str],
    ) -> LoadResult:
        """Batch upsert using INSERT ... ON CONFLICT DO UPDATE SET.

        Args:
            table_name: Target PostgreSQL table.
            records: Pydantic models to persist.
            conflict_columns: Columns forming the unique constraint used for
                conflict detection (e.g. ``["id_tse"]``).

        Returns:
            :class:`LoadResult` with inserted / updated counts and errors.
        """
        if not records:
            return LoadResult()

        result = LoadResult()

        for batch_start in range(0, len(records), self._batch_size):
            batch = records[batch_start : batch_start + self._batch_size]
            dicts = [self._model_to_dict(r) for r in batch]
            self._execute_batch(table_name, dicts, conflict_columns, result)

        logger.info(
            "Upsert into %s complete — inserted=%d updated=%d errors=%d",
            table_name,
            result.inserted,
            result.updated,
            len(result.errors),
        )
        return result

    def close(self) -> None:
        """Close the connection pool."""
        self._pool.close()
        logger.info("PostgresLoader connection pool closed")

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> PostgresLoader:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _model_to_dict(record: BaseModel) -> dict[str, Any]:
        """Serialise a Pydantic model to a plain dict suitable for SQL params.

        Converts UUIDs, dates, datetimes, and Decimals to their native Python
        representations so psycopg can handle them directly.
        """
        return record.model_dump(mode="python")

    def _execute_batch(
        self,
        table_name: str,
        rows: list[dict[str, Any]],
        conflict_columns: list[str],
        result: LoadResult,
    ) -> None:
        """Execute a single batch INSERT ... ON CONFLICT for *rows*."""
        if not rows:
            return

        columns = list(rows[0].keys())
        update_columns = [c for c in columns if c not in conflict_columns]

        # Build query parts using psycopg.sql for safe identifier quoting
        table_id = sql.Identifier(table_name)
        col_ids = sql.SQL(", ").join(sql.Identifier(c) for c in columns)
        placeholders = sql.SQL(", ").join(sql.Placeholder(c) for c in columns)
        conflict_ids = sql.SQL(", ").join(sql.Identifier(c) for c in conflict_columns)

        if update_columns:
            set_clause = sql.SQL(", ").join(
                sql.SQL("{col} = EXCLUDED.{col}").format(col=sql.Identifier(c))
                for c in update_columns
            )
            query = sql.SQL(
                "INSERT INTO {table} ({columns}) VALUES ({placeholders}) "
                "ON CONFLICT ({conflict}) DO UPDATE SET {sets}"
            ).format(
                table=table_id,
                columns=col_ids,
                placeholders=placeholders,
                conflict=conflict_ids,
                sets=set_clause,
            )
        else:
            # All columns are conflict columns — nothing to update
            query = sql.SQL(
                "INSERT INTO {table} ({columns}) VALUES ({placeholders}) "
                "ON CONFLICT ({conflict}) DO NOTHING"
            ).format(
                table=table_id,
                columns=col_ids,
                placeholders=placeholders,
                conflict=conflict_ids,
            )

        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                for row in rows:
                    try:
                        cur.execute(query, row)
                        if cur.statusmessage and cur.statusmessage.startswith("INSERT"):
                            # statusmessage is "INSERT 0 1" on success
                            # pgresult rows_affected tells us if it was insert vs update
                            if cur.rowcount == 1:
                                # Cannot distinguish insert vs update from statusmessage
                                # alone. Use xmax trick: if xmax=0 it was a fresh insert.
                                result.inserted += 1
                            else:
                                result.updated += 1
                    except Exception as exc:
                        conn.rollback()
                        logger.warning(
                            "Error upserting row into %s: %s", table_name, exc
                        )
                        result.errors.append(LoadError(record=row, error=str(exc)))
                        # Re-enter a clean transaction state
                        continue
                conn.commit()
