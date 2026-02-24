"""Neo4jLoader — batch MERGE nodes and relationships into Neo4j."""

from __future__ import annotations

import logging
from typing import Any

from neo4j import GraphDatabase, ManagedTransaction

logger = logging.getLogger(__name__)


class Neo4jLoader:
    """Batch MERGE nodes and relationships into Neo4j.

    Uses UNWIND for efficient batch writes and ``session.execute_write()``
    with explicit transaction functions.
    """

    def __init__(
        self,
        uri: str,
        auth: tuple[str, str],
        batch_size: int = 500,
    ) -> None:
        """
        Args:
            uri: Neo4j bolt URI (e.g. ``bolt://localhost:7687``).
            auth: ``(username, password)`` tuple.
            batch_size: Records per UNWIND batch.
        """
        self._driver = GraphDatabase.driver(uri, auth=auth)
        self._batch_size = batch_size
        logger.info("Neo4jLoader initialised (batch_size=%d)", batch_size)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def merge_nodes(
        self,
        label: str,
        records: list[dict[str, Any]],
        merge_key: str,
    ) -> int:
        """Batch MERGE nodes by a unique key.

        For each record the loader executes::

            UNWIND $records AS r
            MERGE (n:<label> {<merge_key>: r.<merge_key>})
            SET n += r

        Args:
            label: Neo4j node label (e.g. ``Mandatario``).
            records: Dicts of properties to set on each node.
            merge_key: Property used for MERGE matching (must be present in
                every record).

        Returns:
            Total number of nodes merged (created or matched).
        """
        if not records:
            return 0

        total = 0
        for batch in self._batches(records):
            count = self._run_merge_nodes(label, batch, merge_key)
            total += count

        logger.info("Merged %d :%s nodes", total, label)
        return total

    def merge_relationships(
        self,
        rel_type: str,
        from_label: str,
        to_label: str,
        from_key: str,
        to_key: str,
        records: list[dict[str, Any]],
    ) -> int:
        """Batch MERGE relationships between existing nodes.

        Each record must contain ``from_id``, ``to_id``, and optionally
        ``props`` (a dict of properties to set on the relationship).

        Cypher executed per batch::

            UNWIND $records AS r
            MATCH (a:<from_label> {<from_key>: r.from_id})
            MATCH (b:<to_label> {<to_key>: r.to_id})
            MERGE (a)-[rel:<rel_type>]->(b)
            SET rel += r.props

        Args:
            rel_type: Relationship type (e.g. ``FILIADO_A``).
            from_label: Source node label.
            to_label: Target node label.
            from_key: Property on source node to match ``r.from_id``.
            to_key: Property on target node to match ``r.to_id``.
            records: List of dicts with ``from_id``, ``to_id``, and optional
                ``props``.

        Returns:
            Total number of relationships merged.
        """
        if not records:
            return 0

        # Ensure every record has a ``props`` key so Cypher SET does not fail
        normalised = [
            {**r, "props": r.get("props", {})} for r in records
        ]

        total = 0
        for batch in self._batches(normalised):
            count = self._run_merge_relationships(
                rel_type, from_label, to_label, from_key, to_key, batch
            )
            total += count

        logger.info("Merged %d [:%s] relationships", total, rel_type)
        return total

    def close(self) -> None:
        """Close the Neo4j driver."""
        self._driver.close()
        logger.info("Neo4jLoader driver closed")

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> Neo4jLoader:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _batches(self, items: list[Any]) -> list[list[Any]]:
        """Split *items* into chunks of ``self._batch_size``."""
        return [
            items[i : i + self._batch_size]
            for i in range(0, len(items), self._batch_size)
        ]

    def _run_merge_nodes(
        self, label: str, batch: list[dict[str, Any]], merge_key: str
    ) -> int:
        """Execute a single UNWIND-MERGE-nodes transaction."""
        # Neo4j does not support parameterised labels — they must be
        # interpolated into the query string.  We sanitise by allowing
        # only alphanumerics and underscores.
        safe_label = self._sanitise_identifier(label)
        safe_key = self._sanitise_identifier(merge_key)

        cypher = (
            f"UNWIND $records AS r "
            f"MERGE (n:{safe_label} {{{safe_key}: r.{safe_key}}}) "
            f"SET n += r "
            f"RETURN count(n) AS cnt"
        )

        def _work(tx: ManagedTransaction) -> int:
            result = tx.run(cypher, records=batch)
            record = result.single()
            return record["cnt"] if record else 0

        with self._driver.session() as session:
            return session.execute_write(_work)

    def _run_merge_relationships(
        self,
        rel_type: str,
        from_label: str,
        to_label: str,
        from_key: str,
        to_key: str,
        batch: list[dict[str, Any]],
    ) -> int:
        """Execute a single UNWIND-MERGE-relationships transaction."""
        safe_rel = self._sanitise_identifier(rel_type)
        safe_from_label = self._sanitise_identifier(from_label)
        safe_to_label = self._sanitise_identifier(to_label)
        safe_from_key = self._sanitise_identifier(from_key)
        safe_to_key = self._sanitise_identifier(to_key)

        cypher = (
            f"UNWIND $records AS r "
            f"MATCH (a:{safe_from_label} {{{safe_from_key}: r.from_id}}) "
            f"MATCH (b:{safe_to_label} {{{safe_to_key}: r.to_id}}) "
            f"MERGE (a)-[rel:{safe_rel}]->(b) "
            f"SET rel += r.props "
            f"RETURN count(rel) AS cnt"
        )

        def _work(tx: ManagedTransaction) -> int:
            result = tx.run(cypher, records=batch)
            record = result.single()
            return record["cnt"] if record else 0

        with self._driver.session() as session:
            return session.execute_write(_work)

    @staticmethod
    def _sanitise_identifier(name: str) -> str:
        """Ensure a Cypher identifier contains only safe characters.

        Raises:
            ValueError: If *name* contains characters other than
                alphanumerics and underscores.
        """
        cleaned = name.replace("-", "_")
        if not cleaned.isidentifier():
            raise ValueError(
                f"Unsafe Neo4j identifier: {name!r}. "
                "Only alphanumerics and underscores are allowed."
            )
        return cleaned
