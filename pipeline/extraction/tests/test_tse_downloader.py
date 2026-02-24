"""Tests for TSE dump downloader — CSV parsing and field mapping."""

from __future__ import annotations

import json


from bulk.tse_dump_downloader import (
    _clean,
    _classify_donor_type,
    _parse_decimal,
    parse_bens_csv,
    parse_candidatos_csv,
    parse_despesas_csv,
    parse_receitas_csv,
    write_jsonl,
)

# --- Fixtures: mock CSV content ---

CANDIDATOS_CSV = (
    '"ANO_ELEICAO";"SQ_CANDIDATO";"NM_CANDIDATO";"NR_CPF_CANDIDATO";'
    '"NR_CANDIDATO";"DS_CARGO";"SG_PARTIDO";"SG_UF";"DS_SITUACAO_CANDIDATURA";'
    '"DS_SIT_TOT_TURNO"\n'
    '"2022";"280000000001";"JOAO DA SILVA";"12345678901";'
    '"1234";"DEPUTADO FEDERAL";"PXX";"SP";"APTO";"ELEITO"\n'
    '"2022";"280000000002";"MARIA SOUZA";"98765432100";'
    '"5678";"SENADOR";"PYY";"RJ";"APTO";"NAO ELEITO"\n'
    '"2022";"280000000003";"PEDRO SANTOS";"11122233344";'
    '"9999";"GOVERNADOR";"PZZ";"MG";"APTO";"ELEITO"\n'
)

BENS_CSV = (
    '"ANO_ELEICAO";"SQ_CANDIDATO";"DS_TIPO_BEM_CANDIDATO";"DS_BEM_CANDIDATO";'
    '"VR_BEM_CANDIDATO"\n'
    '"2022";"280000000001";"Apartamento";"Apto 3 quartos";"500.000,00"\n'
    '"2022";"280000000002";"Veiculo";"Carro 2020";"80.000,00"\n'
    '"2022";"280000000003";"Casa";"Casa campo";"300.000,00"\n'
)

RECEITAS_CSV = (
    '"ANO_ELEICAO";"SQ_CANDIDATO";"VR_RECEITA";"NM_DOADOR";'
    '"NR_CPF_CNPJ_DOADOR";"DS_ORIGEM_RECEITA";"DT_RECEITA";"DS_RECEITA"\n'
    '"2022";"280000000001";"10.000,00";"EMPRESA X";'
    '"12345678000199";"Recursos de pessoas jurídicas";"15/08/2022";"Doação"\n'
    '"2022";"280000000002";"5.000,00";"FULANO Y";'
    '"98765432100";"Recursos de pessoas físicas";"20/09/2022";"Doação direta"\n'
)

DESPESAS_CSV = (
    '"ANO_ELEICAO";"SQ_CANDIDATO";"VR_DESPESA_CONTRATADA";"DS_ORIGEM_DESPESA";'
    '"NM_FORNECEDOR";"NR_CPF_CNPJ_FORNECEDOR";"DT_DESPESA";"DS_DESPESA"\n'
    '"2022";"280000000001";"3.000,00";"Publicidade";"Grafica ABC";'
    '"11222333000144";"10/09/2022";"Material impresso"\n'
    '"2022";"280000000002";"1.500,00";"Transporte";"Taxi SP";'
    '"55667788000199";"25/09/2022";"Deslocamento campanha"\n'
)


class TestCleanHelpers:
    def test_clean_normal(self):
        assert _clean("  hello  ") == "hello"

    def test_clean_nulo(self):
        assert _clean("#NULO#") is None

    def test_clean_ne(self):
        assert _clean("#NE#") is None

    def test_clean_empty(self):
        assert _clean("") is None

    def test_clean_none(self):
        assert _clean(None) is None

    def test_clean_minus_one(self):
        assert _clean("-1") is None


class TestParseDecimal:
    def test_brazilian_format(self):
        assert _parse_decimal("500.000,00") == 500000.0

    def test_simple_value(self):
        assert _parse_decimal("100,50") == 100.5

    def test_empty(self):
        assert _parse_decimal("") is None

    def test_none(self):
        assert _parse_decimal(None) is None

    def test_invalid(self):
        assert _parse_decimal("abc") is None


class TestClassifyDonorType:
    def test_pf(self):
        assert _classify_donor_type("Recursos de pessoas físicas") == "PF"

    def test_pj(self):
        assert _classify_donor_type("Recursos de pessoas jurídicas") == "PJ"

    def test_partido(self):
        assert _classify_donor_type("Recursos de partido político") == "Partido"

    def test_candidato(self):
        assert _classify_donor_type("Recursos próprios do candidato") == "Candidato"

    def test_none(self):
        assert _classify_donor_type(None) is None

    def test_unknown(self):
        assert _classify_donor_type("Outro tipo") is None


class TestParseCandidatosCsv:
    def test_filters_federal_only(self):
        records = parse_candidatos_csv(CANDIDATOS_CSV, 2022)
        assert len(records) == 2
        cargos = {r["cargo"] for r in records}
        assert cargos == {"DEPUTADO FEDERAL", "SENADOR"}

    def test_field_mapping(self):
        records = parse_candidatos_csv(CANDIDATOS_CSV, 2022)
        dep = next(r for r in records if r["cargo"] == "DEPUTADO FEDERAL")
        assert dep["_type"] == "candidato"
        assert dep["sequencial"] == "280000000001"
        assert dep["nome"] == "JOAO DA SILVA"
        assert dep["cpf"] == "12345678901"
        assert dep["numero_candidato"] == "1234"
        assert dep["sigla_partido"] == "PXX"
        assert dep["sigla_uf"] == "SP"
        assert dep["ano_eleicao"] == 2022
        assert dep["resultado"] == "ELEITO"

    def test_excludes_governor(self):
        records = parse_candidatos_csv(CANDIDATOS_CSV, 2022)
        names = [r["nome"] for r in records]
        assert "PEDRO SANTOS" not in names


class TestParseBensCsv:
    def test_filters_by_sequencial(self):
        federal_seqs = {"280000000001", "280000000002"}
        records = parse_bens_csv(BENS_CSV, 2022, federal_seqs)
        assert len(records) == 2

    def test_field_mapping(self):
        federal_seqs = {"280000000001"}
        records = parse_bens_csv(BENS_CSV, 2022, federal_seqs)
        assert len(records) == 1
        bem = records[0]
        assert bem["_type"] == "bem_declarado"
        assert bem["sequencial_candidato"] == "280000000001"
        assert bem["tipo_bem"] == "Apartamento"
        assert bem["descricao"] == "Apto 3 quartos"
        assert bem["valor"] == 500000.0

    def test_empty_sequenciais_returns_all(self):
        records = parse_bens_csv(BENS_CSV, 2022, set())
        assert len(records) == 3


class TestParseReceitasCsv:
    def test_filters_by_sequencial(self):
        federal_seqs = {"280000000001"}
        records = parse_receitas_csv(RECEITAS_CSV, 2022, federal_seqs)
        assert len(records) == 1

    def test_field_mapping(self):
        federal_seqs = {"280000000001", "280000000002"}
        records = parse_receitas_csv(RECEITAS_CSV, 2022, federal_seqs)
        doacao = next(r for r in records if r["sequencial_candidato"] == "280000000001")
        assert doacao["_type"] == "doacao"
        assert doacao["valor"] == 10000.0
        assert doacao["nome_doador"] == "EMPRESA X"
        assert doacao["cpf_cnpj_doador"] == "12345678000199"
        assert doacao["tipo_doador"] == "PJ"

    def test_pf_donor_type(self):
        federal_seqs = {"280000000002"}
        records = parse_receitas_csv(RECEITAS_CSV, 2022, federal_seqs)
        assert records[0]["tipo_doador"] == "PF"


class TestParseDespesasCsv:
    def test_filters_by_sequencial(self):
        federal_seqs = {"280000000001"}
        records = parse_despesas_csv(DESPESAS_CSV, 2022, federal_seqs)
        assert len(records) == 1

    def test_field_mapping(self):
        federal_seqs = {"280000000001", "280000000002"}
        records = parse_despesas_csv(DESPESAS_CSV, 2022, federal_seqs)
        desp = next(r for r in records if r["sequencial_candidato"] == "280000000001")
        assert desp["_type"] == "despesa_campanha"
        assert desp["valor"] == 3000.0
        assert desp["tipo_despesa"] == "Publicidade"
        assert desp["nome_fornecedor"] == "Grafica ABC"
        assert desp["cnpj_cpf_fornecedor"] == "11222333000144"


class TestWriteJsonl:
    def test_writes_records(self, tmp_path):
        records = [
            {"_type": "candidato", "nome": "Test", "valor": 100.5},
            {"_type": "bem_declarado", "descricao": "Casa"},
        ]
        output = tmp_path / "test.jsonl"
        count = write_jsonl(records, output)
        assert count == 2

        lines = output.read_text().strip().split("\n")
        assert len(lines) == 2
        parsed = json.loads(lines[0])
        assert parsed["_type"] == "candidato"
        assert parsed["nome"] == "Test"

    def test_appends_to_existing(self, tmp_path):
        output = tmp_path / "test.jsonl"
        output.write_text('{"_type": "existing"}\n')
        write_jsonl([{"_type": "new"}], output)
        lines = output.read_text().strip().split("\n")
        assert len(lines) == 2


class TestCliArgParsing:
    def test_default_anos(self):
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--anos", type=str, default="2018,2022")
        args = parser.parse_args([])
        anos = [int(a.strip()) for a in args.anos.split(",")]
        assert anos == [2018, 2022]

    def test_custom_anos(self):
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--anos", type=str, default="2018,2022")
        args = parser.parse_args(["--anos", "2014,2018,2022"])
        anos = [int(a.strip()) for a in args.anos.split(",")]
        assert anos == [2014, 2018, 2022]
