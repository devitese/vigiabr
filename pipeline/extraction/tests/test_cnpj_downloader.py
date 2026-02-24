"""Tests for CNPJ downloader — CSV parsing and field mapping."""

from __future__ import annotations

import json


from bulk.cnpj_downloader import (
    PORTE_MAP,
    _clean,
    _parse_date,
    _parse_decimal,
    _parse_tipo_socio,
    parse_empresas_row,
    parse_estabelecimentos_row,
    parse_socios_row,
    process_csv_file,
)


class TestCleanHelpers:
    def test_clean_normal(self):
        assert _clean("  hello  ") == "hello"

    def test_clean_empty(self):
        assert _clean("") is None

    def test_clean_none(self):
        assert _clean(None) is None

    def test_clean_zero(self):
        assert _clean("0") is None

    def test_clean_quoted(self):
        assert _clean('"value"') == "value"


class TestParseDecimal:
    def test_brazilian_format(self):
        assert _parse_decimal("1.500.000,00") == 1500000.0

    def test_simple(self):
        assert _parse_decimal("100,50") == 100.5

    def test_empty(self):
        assert _parse_decimal("") is None

    def test_none(self):
        assert _parse_decimal(None) is None


class TestParseDate:
    def test_valid_date(self):
        assert _parse_date("20220115") == "2022-01-15"

    def test_zeros(self):
        assert _parse_date("00000000") is None

    def test_empty(self):
        assert _parse_date("") is None

    def test_none(self):
        assert _parse_date(None) is None

    def test_short(self):
        assert _parse_date("2022") is None


class TestParseTipoSocio:
    def test_pj(self):
        assert _parse_tipo_socio("1") == 1

    def test_pf(self):
        assert _parse_tipo_socio("2") == 2

    def test_estrangeiro(self):
        assert _parse_tipo_socio("3") == 3

    def test_invalid(self):
        assert _parse_tipo_socio("5") is None

    def test_none(self):
        assert _parse_tipo_socio(None) is None


class TestPorteMap:
    def test_me(self):
        assert PORTE_MAP["01"] == "ME"

    def test_epp(self):
        assert PORTE_MAP["03"] == "EPP"

    def test_demais(self):
        assert PORTE_MAP["05"] == "DEMAIS"

    def test_nao_informado(self):
        assert PORTE_MAP["00"] == "NAO_INFORMADO"


class TestParseEmpresasRow:
    def test_valid_row(self):
        row = [
            "12345678",
            "EMPRESA TESTE LTDA",
            "2062",
            "49",
            "100.000,00",
            "01",
            "SP",
        ]
        result = parse_empresas_row(row)
        assert result is not None
        assert result["_type"] == "empresa"
        assert result["cnpj_basico"] == "12345678"
        assert result["razao_social"] == "EMPRESA TESTE LTDA"
        assert result["natureza_juridica"] == "2062"
        assert result["qualificacao_responsavel"] == "49"
        assert result["capital_social"] == 100000.0
        assert result["porte"] == "ME"

    def test_missing_required_fields(self):
        row = ["", "", "", "", "", ""]
        assert parse_empresas_row(row) is None

    def test_short_row(self):
        row = ["12345678", "EMPRESA"]
        assert parse_empresas_row(row) is None

    def test_unknown_porte(self):
        row = ["12345678", "EMPRESA X", "2062", "49", "100,00", "99", ""]
        result = parse_empresas_row(row)
        assert result is not None
        assert result["porte"] is None


class TestParseSociosRow:
    def test_valid_row(self):
        row = [
            "12345678",
            "2",
            "FULANO DE TAL",
            "98765432100",
            "49",
            "20200101",
            "",
            "00000000000",
            "REPRESENTANTE",
            "05",
            "4",
        ]
        result = parse_socios_row(row)
        assert result is not None
        assert result["_type"] == "socio"
        assert result["cnpj_basico"] == "12345678"
        assert result["tipo_socio"] == 2
        assert result["nome_socio"] == "FULANO DE TAL"
        assert result["cpf_cnpj_socio"] == "98765432100"
        assert result["qualificacao"] == "49"
        assert result["data_entrada"] == "2020-01-01"
        assert result["percentual_capital"] is None

    def test_missing_nome(self):
        row = ["12345678", "2", "", "98765432100", "49", "20200101", "", ""]
        assert parse_socios_row(row) is None

    def test_invalid_tipo(self):
        row = ["12345678", "5", "NOME", "12345", "49", "20200101", "", ""]
        assert parse_socios_row(row) is None

    def test_short_row(self):
        row = ["12345678", "2", "NOME"]
        assert parse_socios_row(row) is None


class TestParseEstabelecimentosRow:
    def test_valid_row(self):
        row = [
            "12345678",  # 0: cnpj_basico
            "0001",  # 1: cnpj_ordem
            "90",  # 2: cnpj_dv
            "1",  # 3: identificador_matriz
            "FANTASIA",  # 4: nome_fantasia
            "02",  # 5: situacao_cadastral
            "20220115",  # 6: data_situacao
            "01",  # 7: motivo_situacao
            "",  # 8: nome_cidade_exterior
            "",  # 9: pais
            "20100301",  # 10: data_inicio_atividade
            "6201501",  # 11: cnae_principal
            "6202300,6203100",  # 12: cnae_secundario
            "RUA",  # 13: tipo_logradouro
            "DAS FLORES",  # 14: logradouro
            "123",  # 15: numero
            "SALA 1",  # 16: complemento
            "CENTRO",  # 17: bairro
            "01001000",  # 18: cep
            "SP",  # 19: uf
            "7107",  # 20: municipio
        ]
        result = parse_estabelecimentos_row(row)
        assert result is not None
        assert result["_type"] == "estabelecimento"
        assert result["cnpj_basico"] == "12345678"
        assert result["cnpj_ordem"] == "0001"
        assert result["cnpj_dv"] == "90"
        assert result["situacao_cadastral"] == "02"
        assert result["data_situacao"] == "2022-01-15"
        assert result["cnae_principal"] == "6201501"
        assert result["cnaes_secundarios"] == ["6202300", "6203100"]
        assert result["logradouro"] == "RUA DAS FLORES"
        assert result["municipio"] == "7107"
        assert result["uf"] == "SP"
        assert result["cep"] == "01001000"

    def test_missing_cnpj(self):
        row = ["", "0001", "90"] + [""] * 18
        assert parse_estabelecimentos_row(row) is None

    def test_short_row(self):
        row = ["12345678", "0001", "90"]
        assert parse_estabelecimentos_row(row) is None

    def test_no_secondary_cnaes(self):
        row = (
            ["12345678", "0001", "90", "1", "", "02", "20220101", "", "", "", "", "6201501", ""]
            + ["", "FLORES", "", "", "", "01001000", "SP", "7107"]
        )
        result = parse_estabelecimentos_row(row)
        assert result is not None
        assert result["cnaes_secundarios"] == []
        assert result["logradouro"] == "FLORES"


class TestProcessCsvFile:
    def test_empresas_csv(self, tmp_path):
        csv_content = '12345678;"EMPRESA TESTE";"2062";"49";"100.000,00";"01";""\n'
        csv_path = tmp_path / "empresas.csv"
        csv_path.write_text(csv_content, encoding="latin-1")

        output = tmp_path / "output.jsonl"
        count = process_csv_file(csv_path, "empresas", output)
        assert count == 1

        line = output.read_text().strip()
        record = json.loads(line)
        assert record["_type"] == "empresa"
        assert record["cnpj_basico"] == "12345678"
        assert record["razao_social"] == "EMPRESA TESTE"

    def test_socios_csv(self, tmp_path):
        csv_content = (
            '"12345678";"2";"FULANO";"98765432100";"49";"20200101";"";"00000000000";"";"";""\n'
        )
        csv_path = tmp_path / "socios.csv"
        csv_path.write_text(csv_content, encoding="latin-1")

        output = tmp_path / "output.jsonl"
        count = process_csv_file(csv_path, "socios", output)
        assert count == 1

        record = json.loads(output.read_text().strip())
        assert record["_type"] == "socio"
        assert record["nome_socio"] == "FULANO"

    def test_appends_to_existing(self, tmp_path):
        csv_content = '12345678;"EMPRESA A";"2062";"49";"50,00";"03";""\n'
        csv_path = tmp_path / "empresas.csv"
        csv_path.write_text(csv_content, encoding="latin-1")

        output = tmp_path / "output.jsonl"
        output.write_text('{"_type": "existing"}\n')

        process_csv_file(csv_path, "empresas", output)
        lines = output.read_text().strip().split("\n")
        assert len(lines) == 2


class TestCliArgParsing:
    def test_default_tipos(self):
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--tipos",
            type=str,
            default="empresas,socios,estabelecimentos",
        )
        args = parser.parse_args([])
        tipos = [t.strip() for t in args.tipos.split(",")]
        assert tipos == ["empresas", "socios", "estabelecimentos"]

    def test_custom_tipos(self):
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--tipos", type=str, default="empresas,socios,estabelecimentos")
        args = parser.parse_args(["--tipos", "socios"])
        tipos = [t.strip() for t in args.tipos.split(",")]
        assert tipos == ["socios"]
