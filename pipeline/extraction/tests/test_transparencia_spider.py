"""Tests for the Transparencia/CGU spider.

Uses fixture JSON responses to test parsing logic without HTTP calls.
"""

from __future__ import annotations

import json

from scrapy.http import TextResponse, Request

from vigiabr_spiders.spiders.transparencia_cgu import (
    TransparenciaCguSpider,
    _safe_float,
    _nested_str,
    _next_page_url,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_response(url: str, body) -> TextResponse:
    """Build a Scrapy TextResponse from a list/dict (simulates JSON API)."""
    return TextResponse(
        url=url,
        body=json.dumps(body).encode("utf-8"),
        encoding="utf-8",
        request=Request(url=url),
    )


def _collect(generator):
    """Collect yielded items and requests from a spider callback."""
    items = []
    requests = []
    for obj in generator:
        if isinstance(obj, Request):
            requests.append(obj)
        else:
            items.append(obj)
    return items, requests


# ---------------------------------------------------------------------------
# Fixtures — realistic Portal Transparencia API response shapes
# ---------------------------------------------------------------------------

EMENDAS_RESPONSE = [
    {
        "codigoEmenda": "12345678",
        "autor": {"nome": "DEPUTADO FULANO DE TAL"},
        "tipoEmenda": "Individual",
        "ano": 2023,
        "valorEmpenhado": 1500000.00,
        "valorPago": 750000.50,
        "funcao": "Educação",
        "subfuncao": "Ensino Superior",
        "beneficiario": {
            "nome": "Prefeitura de Exemplo",
            "codigoFormatado": "12.345.678/0001-90",
        },
        "localidadeDoGasto": "Exemplo - UF",
    },
    {
        "codigoEmenda": "87654321",
        "autor": {"nome": "SENADORA BELTRANA"},
        "tipoEmenda": "Bancada",
        "ano": 2023,
        "valorEmpenhado": None,
        "valorPago": 200000.00,
        "nomeFuncao": "Saúde",
        "nomeSubfuncao": "Atenção Básica",
    },
]

EMENDAS_FLAT_AUTOR = [
    {
        "codigoEmenda": "99999",
        "autor": "DEPUTADO LEGADO",
        "ano": 2024,
        "valorPago": 100000,
    },
]

CONTRATOS_RESPONSE = [
    {
        "numero": "CT-001/2023",
        "unidadeGestora": {"nome": "Ministério da Educação"},
        "objeto": "Fornecimento de equipamentos de informática",
        "valorInicial": 5000000.00,
        "dataAssinatura": "2023-06-15",
        "dataFimVigencia": "2024-06-15",
        "fornecedor": {
            "cnpjCpf": "98765432000199",
            "nome": "Tech Corp Ltda",
        },
        "modalidadeLicitacao": "Pregão Eletrônico",
    },
    {
        "id": "CT-002/2023",
        "orgao": {"descricao": "Ministério da Saúde"},
        "objetoContrato": "Serviços de limpeza",
        "valor": 120000.00,
        "dataInicioVigencia": "2023-01-01",
        "contratado": {
            "codigoFormatado": "11.222.333/0001-44",
            "razaoSocial": "Limpeza Total SA",
        },
        "modalidadeCompra": "Dispensa de Licitação",
    },
]

CEIS_RESPONSE = [
    {
        "sancionado": {
            "cnpjCpf": "12345678000100",
            "nome": "Empresa Inidônea Ltda",
        },
        "tipoSancao": "Inidoneidade",
        "orgaoSancionador": {"nome": "CGU"},
        "dataInicioSancao": "2022-01-15",
        "dataFimSancao": "2025-01-15",
    },
    {
        "pessoa": {
            "codigoFormatado": "987.654.321-00",
            "razaoSocial": "Pessoa Física Punida",
        },
        "fundamentacaoLegal": "Lei 8.666/93 Art. 87",
        "orgaoSancionador": {"descricao": "Tribunal de Contas"},
        "dataInicio": "2023-06-01",
    },
]

CARTOES_RESPONSE = [
    {
        "portador": {
            "cpf": "12345678900",
            "nome": "JOAO DA SILVA",
        },
        "valorTransacao": 1500.75,
        "dataTransacao": "2023-03-15",
        "estabelecimento": {
            "nomeFantasia": "Restaurante Exemplo",
            "cnpj": "11222333000144",
        },
    },
    {
        "portador": {
            "cpfFormatado": "987.654.321-00",
            "nome": "MARIA SOUZA",
        },
        "valor": 250.00,
        "data": "2023-04-20",
        "estabelecimento": {
            "nome": "Posto Combustivel",
            "cnpjFormatado": "55.666.777/0001-88",
        },
    },
]


# ---------------------------------------------------------------------------
# Tests — Helper functions
# ---------------------------------------------------------------------------

class TestSafeFloat:
    def test_valid_float(self):
        assert _safe_float(123.45) == 123.45

    def test_string_float(self):
        assert _safe_float("123.45") == 123.45

    def test_comma_decimal(self):
        assert _safe_float("1.234,56") == 1234.56  # Brazilian format

    def test_none_returns_none(self):
        assert _safe_float(None) is None

    def test_invalid_string_returns_none(self):
        assert _safe_float("not-a-number") is None

    def test_zero(self):
        assert _safe_float(0) == 0.0

    def test_integer(self):
        assert _safe_float(100) == 100.0


class TestNestedStr:
    def test_nested_value(self):
        record = {"a": {"b": "hello"}}
        assert _nested_str(record, "a", "b") == "hello"

    def test_missing_key_returns_none(self):
        record = {"a": {"b": "hello"}}
        assert _nested_str(record, "a", "c") is None

    def test_missing_parent_returns_none(self):
        record = {"x": 1}
        assert _nested_str(record, "a", "b") is None

    def test_empty_string_returns_none(self):
        record = {"a": {"b": ""}}
        assert _nested_str(record, "a", "b") is None

    def test_whitespace_only_returns_none(self):
        record = {"a": {"b": "   "}}
        assert _nested_str(record, "a", "b") is None

    def test_none_value_returns_none(self):
        record = {"a": {"b": None}}
        assert _nested_str(record, "a", "b") is None

    def test_single_key(self):
        record = {"key": "value"}
        assert _nested_str(record, "key") == "value"


class TestNextPageUrl:
    def test_increments_page(self):
        url = "https://api.example.com/data?ano=2023&pagina=1"
        assert _next_page_url(url) == "https://api.example.com/data?ano=2023&pagina=2"

    def test_increments_higher_page(self):
        url = "https://api.example.com/data?pagina=99"
        assert _next_page_url(url) == "https://api.example.com/data?pagina=100"

    def test_preserves_other_params(self):
        url = "https://api.example.com/data?foo=bar&pagina=3&baz=qux"
        result = _next_page_url(url)
        assert "pagina=4" in result
        assert "foo=bar" in result
        assert "baz=qux" in result


# ---------------------------------------------------------------------------
# Tests — Emenda parsing
# ---------------------------------------------------------------------------

class TestParseEmendas:
    def setup_method(self):
        self.spider = TransparenciaCguSpider()

    def test_parses_multiple_emendas(self):
        resp = _fake_response(
            f"{self.spider.BASE_URL}/emendas?ano=2023&pagina=1",
            EMENDAS_RESPONSE,
        )
        items, requests = _collect(self.spider.parse_emendas(resp, ano=2023))
        assert len(items) == 2
        assert all(i["_type"] == "emenda" for i in items)

    def test_emenda_field_mapping(self):
        resp = _fake_response(
            f"{self.spider.BASE_URL}/emendas?ano=2023&pagina=1",
            EMENDAS_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_emendas(resp, ano=2023))

        e = items[0]
        assert e["numero"] == "12345678"
        assert e["autor"] == "DEPUTADO FULANO DE TAL"
        assert e["tipo"] == "Individual"
        assert e["ano"] == 2023
        assert e["valor_empenhado"] == 1500000.00
        assert e["valor_pago"] == 750000.50
        assert e["funcao"] == "Educação"
        assert e["subfuncao"] == "Ensino Superior"
        assert e["beneficiario_nome"] == "Prefeitura de Exemplo"
        assert e["beneficiario_cnpj_cpf"] == "12.345.678/0001-90"
        assert e["localidade"] == "Exemplo - UF"

    def test_emenda_missing_optional_fields(self):
        resp = _fake_response(
            f"{self.spider.BASE_URL}/emendas?ano=2023&pagina=1",
            EMENDAS_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_emendas(resp, ano=2023))

        e = items[1]
        assert e["valor_empenhado"] is None
        assert e["beneficiario_nome"] is None
        assert e["beneficiario_cnpj_cpf"] is None
        assert e["localidade"] is None
        # Fallback field names
        assert e["funcao"] == "Saúde"
        assert e["subfuncao"] == "Atenção Básica"

    def test_emenda_flat_autor_string(self):
        """Older API format may return autor as a plain string."""
        resp = _fake_response(
            f"{self.spider.BASE_URL}/emendas?ano=2024&pagina=1",
            EMENDAS_FLAT_AUTOR,
        )
        items, _ = _collect(self.spider.parse_emendas(resp, ano=2024))
        assert items[0]["autor"] == "DEPUTADO LEGADO"

    def test_emenda_empty_response_stops(self):
        resp = _fake_response(
            f"{self.spider.BASE_URL}/emendas?ano=2023&pagina=5",
            [],
        )
        items, requests = _collect(self.spider.parse_emendas(resp, ano=2023))
        assert items == []
        assert requests == []

    def test_emenda_pagination_continues(self):
        """If response has PAGE_SIZE items, spider should request next page."""
        full_page = [EMENDAS_RESPONSE[0]] * TransparenciaCguSpider.PAGE_SIZE
        resp = _fake_response(
            f"{self.spider.BASE_URL}/emendas?ano=2023&pagina=1",
            full_page,
        )
        items, requests = _collect(self.spider.parse_emendas(resp, ano=2023))
        assert len(items) == TransparenciaCguSpider.PAGE_SIZE
        assert len(requests) == 1
        assert "pagina=2" in requests[0].url

    def test_emenda_pagination_stops_on_partial_page(self):
        """If response has fewer items than PAGE_SIZE, stop paginating."""
        partial = [EMENDAS_RESPONSE[0]] * (TransparenciaCguSpider.PAGE_SIZE - 1)
        resp = _fake_response(
            f"{self.spider.BASE_URL}/emendas?ano=2023&pagina=3",
            partial,
        )
        items, requests = _collect(self.spider.parse_emendas(resp, ano=2023))
        assert len(items) == TransparenciaCguSpider.PAGE_SIZE - 1
        assert requests == []


# ---------------------------------------------------------------------------
# Tests — Contrato parsing
# ---------------------------------------------------------------------------

class TestParseContratos:
    def setup_method(self):
        self.spider = TransparenciaCguSpider()

    def test_parses_multiple_contratos(self):
        resp = _fake_response(
            f"{self.spider.BASE_URL}/contratos?pagina=1",
            CONTRATOS_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_contratos(resp))
        assert len(items) == 2
        assert all(i["_type"] == "contrato" for i in items)

    def test_contrato_field_mapping_primary(self):
        resp = _fake_response(
            f"{self.spider.BASE_URL}/contratos?pagina=1",
            CONTRATOS_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_contratos(resp))

        c = items[0]
        assert c["numero"] == "CT-001/2023"
        assert c["orgao"] == "Ministério da Educação"
        assert c["objeto"] == "Fornecimento de equipamentos de informática"
        assert c["valor"] == 5000000.00
        assert c["data_assinatura"] == "2023-06-15"
        assert c["data_fim_vigencia"] == "2024-06-15"
        assert c["cnpj_contratado"] == "98765432000199"
        assert c["nome_contratado"] == "Tech Corp Ltda"
        assert c["modalidade_licitacao"] == "Pregão Eletrônico"

    def test_contrato_field_mapping_fallback(self):
        """Tests fallback field names (id, orgao.descricao, etc.)."""
        resp = _fake_response(
            f"{self.spider.BASE_URL}/contratos?pagina=1",
            CONTRATOS_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_contratos(resp))

        c = items[1]
        assert c["numero"] == "CT-002/2023"
        assert c["orgao"] == "Ministério da Saúde"
        assert c["objeto"] == "Serviços de limpeza"
        assert c["valor"] == 120000.00
        assert c["data_assinatura"] == "2023-01-01"
        assert c["cnpj_contratado"] == "11.222.333/0001-44"
        assert c["nome_contratado"] == "Limpeza Total SA"
        assert c["modalidade_licitacao"] == "Dispensa de Licitação"

    def test_contrato_empty_response_stops(self):
        resp = _fake_response(
            f"{self.spider.BASE_URL}/contratos?pagina=10",
            [],
        )
        items, requests = _collect(self.spider.parse_contratos(resp))
        assert items == []
        assert requests == []

    def test_contrato_pagination(self):
        full_page = [CONTRATOS_RESPONSE[0]] * TransparenciaCguSpider.PAGE_SIZE
        resp = _fake_response(
            f"{self.spider.BASE_URL}/contratos?pagina=1",
            full_page,
        )
        items, requests = _collect(self.spider.parse_contratos(resp))
        assert len(requests) == 1
        assert "pagina=2" in requests[0].url


# ---------------------------------------------------------------------------
# Tests — CEIS parsing
# ---------------------------------------------------------------------------

class TestParseCeis:
    def setup_method(self):
        self.spider = TransparenciaCguSpider()

    def test_parses_ceis_records(self):
        resp = _fake_response(
            f"{self.spider.BASE_URL}/ceis?pagina=1",
            CEIS_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_ceis(resp))
        assert len(items) == 2
        assert all(i["_type"] == "ceis" for i in items)

    def test_ceis_field_mapping_primary(self):
        resp = _fake_response(
            f"{self.spider.BASE_URL}/ceis?pagina=1",
            CEIS_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_ceis(resp))

        c = items[0]
        assert c["cnpj_cpf"] == "12345678000100"
        assert c["nome"] == "Empresa Inidônea Ltda"
        assert c["tipo_sancao"] == "Inidoneidade"
        assert c["orgao_sancionador"] == "CGU"
        assert c["data_inicio"] == "2022-01-15"
        assert c["data_fim"] == "2025-01-15"

    def test_ceis_field_mapping_fallback(self):
        """Tests fallback field names (pessoa, fundamentacaoLegal, etc.)."""
        resp = _fake_response(
            f"{self.spider.BASE_URL}/ceis?pagina=1",
            CEIS_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_ceis(resp))

        c = items[1]
        assert c["cnpj_cpf"] == "987.654.321-00"
        assert c["nome"] == "Pessoa Física Punida"
        assert c["tipo_sancao"] == "Lei 8.666/93 Art. 87"
        assert c["orgao_sancionador"] == "Tribunal de Contas"
        assert c["data_inicio"] == "2023-06-01"
        assert c["data_fim"] is None

    def test_ceis_empty_response_stops(self):
        resp = _fake_response(
            f"{self.spider.BASE_URL}/ceis?pagina=5",
            [],
        )
        items, requests = _collect(self.spider.parse_ceis(resp))
        assert items == []
        assert requests == []

    def test_ceis_pagination(self):
        full_page = [CEIS_RESPONSE[0]] * TransparenciaCguSpider.PAGE_SIZE
        resp = _fake_response(
            f"{self.spider.BASE_URL}/ceis?pagina=1",
            full_page,
        )
        items, requests = _collect(self.spider.parse_ceis(resp))
        assert len(requests) == 1
        assert "pagina=2" in requests[0].url


# ---------------------------------------------------------------------------
# Tests — Cartao corporativo parsing
# ---------------------------------------------------------------------------

class TestParseCartoes:
    def setup_method(self):
        self.spider = TransparenciaCguSpider()

    def test_parses_cartao_records(self):
        resp = _fake_response(
            f"{self.spider.BASE_URL}/cartoes?mesExtratoInicio=03&mesExtratoFim=03&anoExtratoInicio=2023&anoExtratoFim=2023&pagina=1",
            CARTOES_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_cartoes(resp))
        assert len(items) == 2
        assert all(i["_type"] == "cartao_corporativo" for i in items)

    def test_cartao_field_mapping_primary(self):
        resp = _fake_response(
            f"{self.spider.BASE_URL}/cartoes?pagina=1",
            CARTOES_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_cartoes(resp))

        c = items[0]
        assert c["cpf_portador"] == "12345678900"
        assert c["nome_portador"] == "JOAO DA SILVA"
        assert c["valor"] == 1500.75
        assert c["data"] == "2023-03-15"
        assert c["estabelecimento"] == "Restaurante Exemplo"
        assert c["cnpj_estabelecimento"] == "11222333000144"

    def test_cartao_field_mapping_fallback(self):
        """Tests fallback field names (cpfFormatado, valor, data, etc.)."""
        resp = _fake_response(
            f"{self.spider.BASE_URL}/cartoes?pagina=1",
            CARTOES_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_cartoes(resp))

        c = items[1]
        assert c["cpf_portador"] == "987.654.321-00"
        assert c["nome_portador"] == "MARIA SOUZA"
        assert c["valor"] == 250.00
        assert c["data"] == "2023-04-20"
        assert c["estabelecimento"] == "Posto Combustivel"
        assert c["cnpj_estabelecimento"] == "55.666.777/0001-88"

    def test_cartao_empty_response_stops(self):
        resp = _fake_response(
            f"{self.spider.BASE_URL}/cartoes?pagina=5",
            [],
        )
        items, requests = _collect(self.spider.parse_cartoes(resp))
        assert items == []
        assert requests == []

    def test_cartao_pagination(self):
        full_page = [CARTOES_RESPONSE[0]] * TransparenciaCguSpider.PAGE_SIZE
        resp = _fake_response(
            f"{self.spider.BASE_URL}/cartoes?pagina=1",
            full_page,
        )
        items, requests = _collect(self.spider.parse_cartoes(resp))
        assert len(requests) == 1
        assert "pagina=2" in requests[0].url


# ---------------------------------------------------------------------------
# Tests — Start requests
# ---------------------------------------------------------------------------

class TestStartRequests:
    def test_generates_initial_requests(self):
        spider = TransparenciaCguSpider()
        requests = list(spider.start_requests())
        urls = [r.url for r in requests]

        # Emendas: one per year
        emenda_urls = [u for u in urls if "/emendas" in u]
        assert len(emenda_urls) == len(TransparenciaCguSpider.EMENDA_YEARS)
        for ano in TransparenciaCguSpider.EMENDA_YEARS:
            assert any(f"ano={ano}" in u for u in emenda_urls)

        # Contratos: one initial request
        contrato_urls = [u for u in urls if "/contratos" in u]
        assert len(contrato_urls) == 1

        # CEIS: one initial request
        ceis_urls = [u for u in urls if "/ceis" in u]
        assert len(ceis_urls) == 1

        # Cartoes: one per year/month
        cartao_urls = [u for u in urls if "/cartoes" in u]
        assert len(cartao_urls) == len(TransparenciaCguSpider.EMENDA_YEARS) * 12

    def test_all_requests_start_at_page_1(self):
        spider = TransparenciaCguSpider()
        requests = list(spider.start_requests())
        for r in requests:
            assert "pagina=1" in r.url

    def test_custom_settings(self):
        spider = TransparenciaCguSpider()
        assert spider.custom_settings["ROBOTSTXT_OBEY"] is False
        assert spider.custom_settings["DOWNLOAD_DELAY"] == 0.2


# ---------------------------------------------------------------------------
# Tests — Spider attributes
# ---------------------------------------------------------------------------

class TestSpiderAttributes:
    def test_name(self):
        spider = TransparenciaCguSpider()
        assert spider.name == "transparencia_cgu"

    def test_source_name(self):
        spider = TransparenciaCguSpider()
        assert spider.source_name == "transparencia"

    def test_allowed_domains(self):
        spider = TransparenciaCguSpider()
        assert "api.portaldatransparencia.gov.br" in spider.allowed_domains
