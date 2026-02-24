"""VigiaBR loaders — persist validated data to PostgreSQL, Neo4j, and local stores."""

from processing.loaders.cnpj_local_loader import CnpjLocalLoader
from processing.loaders.neo4j_loader import Neo4jLoader
from processing.loaders.postgres_loader import LoadError, LoadResult, PostgresLoader

__all__ = [
    "CnpjLocalLoader",
    "LoadError",
    "LoadResult",
    "Neo4jLoader",
    "PostgresLoader",
]
