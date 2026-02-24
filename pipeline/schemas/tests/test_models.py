"""Tests for SQLAlchemy ORM models and Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.base import Base
from models.mandatario import MandatarioSchema, MandatarioCreateSchema
from models.partido import Partido, PartidoSchema
from models.pessoa_fisica import PessoaFisicaSchema, TipoPessoa
from models.empresa import EmpresaSchema
from models.inconsistencia import InconsistenciaSchema
import models.relationships  # noqa: F401 — registers junction tables in Base.metadata


@pytest.fixture
def engine():
    """In-memory SQLite engine for testing (excludes PG-only tables)."""
    engine = create_engine("sqlite:///:memory:")
    # Exclude tables with PG-specific types (ARRAY) that SQLite can't handle.
    # The inconsistencias table uses ARRAY(String) — tested via Pydantic schemas only.
    tables_to_create = [
        t for t in Base.metadata.sorted_tables if t.name != "inconsistencias"
    ]
    Base.metadata.create_all(engine, tables=tables_to_create)
    return engine


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


class TestTableCreation:
    """Verify all tables are registered in metadata."""

    def test_all_tables_in_metadata(self):
        """Check all expected tables are in SQLAlchemy metadata (no DB needed)."""
        table_names = set(Base.metadata.tables.keys())

        expected = [
            "mandatarios",
            "partidos",
            "pessoas_fisicas",
            "empresas",
            "bens_patrimoniais",
            "emendas",
            "contratos_gov",
            "votacoes",
            "projetos_lei",
            "processos_judiciais",
            "inconsistencias",
            "mandatario_votos",
            "mandatario_filiacoes",
            "mandatario_familiares",
            "mandatario_contratacoes",
            "pessoa_empresa_socios",
            "doacoes",
        ]

        for table in expected:
            assert table in table_names, f"Missing table: {table}"

    def test_sqlite_compatible_tables_create(self, engine):
        """Tables without PG-specific types should create in SQLite."""
        from sqlalchemy import inspect

        inspector = inspect(engine)
        tables = inspector.get_table_names()
        # At minimum, the core tables (minus inconsistencias) should exist
        assert "mandatarios" in tables
        assert "partidos" in tables
        assert "empresas" in tables
        assert "votacoes" in tables


class TestPydanticSchemas:
    """Verify Pydantic schemas validate correctly."""

    def test_mandatario_schema(self):
        now = datetime.now(tz=timezone.utc)
        schema = MandatarioSchema(
            id=uuid.uuid4(),
            id_tse="12345",
            nome="João da Silva",
            cargo="Deputado Federal",
            uf="SP",
            partido_sigla="PT",
            sci_score=750,
            created_at=now,
            updated_at=now,
        )
        assert schema.sci_score == 750
        assert schema.uf == "SP"

    def test_mandatario_create_schema(self):
        schema = MandatarioCreateSchema(
            id_tse="12345",
            nome="João da Silva",
            cargo="Deputado Federal",
            uf="SP",
        )
        assert schema.nome == "João da Silva"

    def test_mandatario_sci_score_validation(self):
        now = datetime.now(tz=timezone.utc)
        with pytest.raises(Exception):
            MandatarioSchema(
                id=uuid.uuid4(),
                id_tse="12345",
                nome="Test",
                cargo="Deputado",
                uf="SP",
                sci_score=1500,
                created_at=now,
                updated_at=now,
            )

    def test_partido_schema(self):
        now = datetime.now(tz=timezone.utc)
        schema = PartidoSchema(
            id=uuid.uuid4(),
            sigla="PT",
            nome="Partido dos Trabalhadores",
            numero_eleitoral=13,
            created_at=now,
            updated_at=now,
        )
        assert schema.sigla == "PT"

    def test_pessoa_fisica_schema_cpf_hash_length(self):
        now = datetime.now(tz=timezone.utc)
        short_hash = "abc"
        with pytest.raises(Exception):
            PessoaFisicaSchema(
                id=uuid.uuid4(),
                nome="Maria",
                cpf_hash=short_hash,
                tipo=TipoPessoa.FAMILIAR,
                created_at=now,
                updated_at=now,
            )

    def test_empresa_schema(self):
        now = datetime.now(tz=timezone.utc)
        schema = EmpresaSchema(
            id=uuid.uuid4(),
            cnpj="12.345.678/0001-95",
            razao_social="Empresa Teste LTDA",
            capital_social=Decimal("1000000.00"),
            created_at=now,
            updated_at=now,
        )
        assert schema.capital_social == Decimal("1000000.00")

    def test_inconsistencia_score_range(self):
        now = datetime.now(tz=timezone.utc)
        with pytest.raises(Exception):
            InconsistenciaSchema(
                id=uuid.uuid4(),
                tipo="patrimonio",
                descricao_neutra="Test",
                score_impacto=300,
                fontes=[],
                data_deteccao=date.today(),
                created_at=now,
                updated_at=now,
            )


class TestFromAttributes:
    """Verify Pydantic schemas can load from ORM objects."""

    def test_from_orm_partido(self, session):
        partido = Partido(sigla="PSOL", nome="Partido Socialismo e Liberdade", numero_eleitoral=50)
        session.add(partido)
        session.flush()

        schema = PartidoSchema.model_validate(partido)
        assert schema.sigla == "PSOL"
        assert schema.nome == "Partido Socialismo e Liberdade"
