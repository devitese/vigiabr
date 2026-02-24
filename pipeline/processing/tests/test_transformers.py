"""Tests for processing transformers — pure logic, no external I/O."""

from __future__ import annotations

import logging
from pathlib import Path

from models.mandatario import MandatarioCreateSchema
from models.projeto_lei import ProjetoLeiCreateSchema
from pii import hash_cpf

from processing.transformers.base import (
    BaseTransformer,
    MandatarioVotoCreateSchema,
    TransformResult,
    VotacaoCreateSchema,
)
from processing.transformers.camara import CamaraTransformer


# -------------------------------------------------------------------- #
# CamaraTransformer tests                                               #
# -------------------------------------------------------------------- #


class TestCamaraTransformDeputado:
    """Test CamaraTransformer._transform_deputado via .transform()."""

    def test_transform_deputado(self):
        """A valid deputado dict produces a MandatarioCreateSchema with hashed CPF."""
        record = {
            "type": "deputado",
            "id": 204554,
            "nome": "Fulano da Silva",
            "nome_civil": "Fulano Almeida da Silva",
            "cpf": "12345678901",
            "sigla_partido": "PT",
            "sigla_uf": "SP",
        }

        transformer = CamaraTransformer()
        result = transformer.transform(iter([record]))

        assert result.total_entities == 1
        assert len(result.errors) == 0

        mandatarios = result.entities["mandatarios"]
        assert len(mandatarios) == 1

        m = mandatarios[0]
        assert isinstance(m, MandatarioCreateSchema)
        assert m.nome == "Fulano da Silva"
        assert m.nome_civil == "Fulano Almeida da Silva"
        assert m.cargo == "Deputado Federal"
        assert m.uf == "SP"
        assert m.partido_sigla == "PT"
        assert m.id_tse == "204554"
        # CPF must be hashed, never raw
        assert m.cpf_hash is not None
        assert len(m.cpf_hash) == 64
        assert m.cpf_hash == hash_cpf("12345678901")

    def test_transform_deputado_no_cpf(self):
        """A deputado record without CPF produces cpf_hash=None."""
        record = {
            "type": "deputado",
            "id": 204555,
            "nome": "Ciclana Souza",
            "sigla_partido": "PSOL",
            "sigla_uf": "RJ",
        }

        transformer = CamaraTransformer()
        result = transformer.transform(iter([record]))

        assert result.total_entities == 1
        m = result.entities["mandatarios"][0]
        assert m.cpf_hash is None


class TestCamaraTransformVotacao:
    """Test CamaraTransformer._transform_votacao via .transform()."""

    def test_transform_votacao(self):
        """A votacao dict with 2 votes produces 1 entity + 2 relationships."""
        record = {
            "type": "votacao",
            "id_votacao": "VOT-2024-001",
            "data": "2024-06-15T14:30:00",
            "descricao": "PL 123/2024 - Aprovacao",
            "votos": [
                {"id_deputado": 100, "voto": "Sim"},
                {"id_deputado": 200, "voto": "Não"},
            ],
        }

        transformer = CamaraTransformer()
        result = transformer.transform(iter([record]))

        # 1 votacao entity
        votacoes = result.entities.get("votacoes", [])
        assert len(votacoes) == 1
        v = votacoes[0]
        assert isinstance(v, VotacaoCreateSchema)
        assert v.id_externo == "VOT-2024-001"
        assert v.descricao == "PL 123/2024 - Aprovacao"

        # 2 mandatario_voto relationships
        votos = result.relationships.get("mandatario_votos", [])
        assert len(votos) == 2
        assert all(isinstance(vt, MandatarioVotoCreateSchema) for vt in votos)
        assert votos[0].mandatario_id_externo == "100"
        assert votos[0].voto == "Sim"
        assert votos[1].mandatario_id_externo == "200"
        assert votos[1].voto == "Não"


class TestCamaraTransformProposicao:
    """Test CamaraTransformer._transform_proposicao via .transform()."""

    def test_transform_proposicao(self):
        """A proposicao dict produces a ProjetoLeiCreateSchema."""
        record = {
            "type": "proposicao",
            "id": 99999,
            "tipo": "PL",
            "numero": 123,
            "ano": 2024,
            "ementa": "Dispoe sobre transparencia.",
            "situacao": "Em tramitacao",
            "tema": "Administracao Publica",
        }

        transformer = CamaraTransformer()
        result = transformer.transform(iter([record]))

        projetos = result.entities.get("projetos_lei", [])
        assert len(projetos) == 1
        p = projetos[0]
        assert isinstance(p, ProjetoLeiCreateSchema)
        assert p.numero == 123
        assert p.ano == 2024
        assert p.tipo == "PL"
        assert p.ementa == "Dispoe sobre transparencia."
        assert p.situacao == "Em tramitacao"
        assert p.tema == "Administracao Publica"


class TestCamaraSkippedAndInvalid:
    """Test skipped types and malformed records."""

    def test_skipped_types(self):
        """Despesa records (MVP-skipped) produce no entities and no errors."""
        record = {
            "type": "despesa",
            "id_deputado": 100,
            "ano": 2024,
            "mes": 6,
            "tipo_despesa": "PASSAGENS",
            "valor_liquido": "150.00",
        }

        transformer = CamaraTransformer()
        result = transformer.transform(iter([record]))

        assert result.total_entities == 0
        assert result.total_relationships == 0
        assert len(result.errors) == 0

    def test_invalid_record_is_error(self):
        """A malformed deputado record shows up in errors, doesn't crash."""
        record = {
            "type": "deputado",
            # Missing required fields: id, nome, sigla_partido, sigla_uf
        }

        transformer = CamaraTransformer()
        result = transformer.transform(iter([record]))

        assert result.total_entities == 0
        assert len(result.errors) == 1
        assert result.errors[0].source == "camara"
        assert "deputado" in result.errors[0].record.get("type", "")


# -------------------------------------------------------------------- #
# BaseTransformer tests                                                  #
# -------------------------------------------------------------------- #


class ConcreteTransformer(BaseTransformer):
    """Minimal concrete subclass for testing base methods."""

    source_name: str = "test_source"

    def transform(self, raw_records):
        return TransformResult()


class TestBaseTransformerReadJsonl:
    """Test BaseTransformer.read_jsonl()."""

    def test_read_jsonl(self, tmp_path: Path):
        """Valid JSONL file is parsed correctly."""
        jsonl_file = tmp_path / "data.jsonl"
        jsonl_file.write_text(
            '{"id": 1, "name": "Alice"}\n'
            '{"id": 2, "name": "Bob"}\n'
            '{"id": 3, "name": "Charlie"}\n',
            encoding="utf-8",
        )

        transformer = ConcreteTransformer()
        records = list(transformer.read_jsonl(jsonl_file))

        assert len(records) == 3
        assert records[0] == {"id": 1, "name": "Alice"}
        assert records[1] == {"id": 2, "name": "Bob"}
        assert records[2] == {"id": 3, "name": "Charlie"}

    def test_read_jsonl_malformed_line(self, tmp_path: Path, caplog):
        """Malformed lines are skipped and logged; valid lines still parsed."""
        jsonl_file = tmp_path / "mixed.jsonl"
        jsonl_file.write_text(
            '{"id": 1, "valid": true}\n'
            "this is not json\n"
            '{"id": 2, "valid": true}\n',
            encoding="utf-8",
        )

        transformer = ConcreteTransformer()
        with caplog.at_level(logging.WARNING):
            records = list(transformer.read_jsonl(jsonl_file))

        assert len(records) == 2
        assert records[0]["id"] == 1
        assert records[1]["id"] == 2
        # Verify the malformed line was logged
        assert any("invalid JSON" in msg for msg in caplog.messages)


class TestBaseTransformerFindLatestRun:
    """Test BaseTransformer.find_latest_run()."""

    def test_find_latest_run(self, tmp_path: Path):
        """Given two date-named dirs, the lexicographically latest is returned."""
        source_dir = tmp_path / "data" / "raw" / "test_source"
        source_dir.mkdir(parents=True)

        (source_dir / "2024-01-15").mkdir()
        (source_dir / "2024-06-20").mkdir()

        transformer = ConcreteTransformer()
        latest = transformer.find_latest_run(tmp_path)

        assert latest is not None
        assert latest.name == "2024-06-20"

    def test_find_latest_run_no_dirs(self, tmp_path: Path):
        """Returns None when the source directory has no subdirectories."""
        source_dir = tmp_path / "data" / "raw" / "test_source"
        source_dir.mkdir(parents=True)

        transformer = ConcreteTransformer()
        latest = transformer.find_latest_run(tmp_path)

        assert latest is None

    def test_find_latest_run_missing_source_dir(self, tmp_path: Path):
        """Returns None when the source directory doesn't exist at all."""
        transformer = ConcreteTransformer()
        latest = transformer.find_latest_run(tmp_path)

        assert latest is None


# -------------------------------------------------------------------- #
# TransformResult tests                                                  #
# -------------------------------------------------------------------- #


class TestTransformResult:
    """Test TransformResult data structure."""

    def test_add_entity_and_relationship(self):
        """add_entity and add_relationship store objects correctly."""
        result = TransformResult()

        entity_a = {"id": "a"}
        entity_b = {"id": "b"}
        rel = {"from": "a", "to": "b"}

        result.add_entity("mandatarios", entity_a)
        result.add_entity("mandatarios", entity_b)
        result.add_relationship("mandatario_votos", rel)

        assert len(result.entities["mandatarios"]) == 2
        assert result.entities["mandatarios"][0] == entity_a
        assert result.entities["mandatarios"][1] == entity_b
        assert len(result.relationships["mandatario_votos"]) == 1
        assert result.relationships["mandatario_votos"][0] == rel

    def test_total_entities_and_relationships(self):
        """total_entities and total_relationships count across all tables."""
        result = TransformResult()

        result.add_entity("mandatarios", {"id": 1})
        result.add_entity("mandatarios", {"id": 2})
        result.add_entity("votacoes", {"id": 3})
        result.add_relationship("mandatario_votos", {"a": 1})

        assert result.total_entities == 3
        assert result.total_relationships == 1

    def test_empty_result(self):
        """A fresh TransformResult has zero counts."""
        result = TransformResult()
        assert result.total_entities == 0
        assert result.total_relationships == 0
        assert len(result.errors) == 0

    def test_add_error(self):
        """add_error appends TransformError objects correctly."""
        result = TransformResult()
        result.add_error({"bad": "record"}, "missing field", "camara")

        assert len(result.errors) == 1
        assert result.errors[0].record == {"bad": "record"}
        assert result.errors[0].error == "missing field"
        assert result.errors[0].source == "camara"
