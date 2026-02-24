"""Tests for the Camara dos Deputados spider.

Uses fake JSON responses — no real HTTP calls.
"""

from __future__ import annotations

import json
from typing import Any

from scrapy.http import Request, TextResponse

from vigiabr_spiders.spiders.camara_deputados import (
    CamaraDeputadosSpider,
    _extract_proposicao_id,
    _month_end,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _fake_response(url: str, body: dict | list, *, meta: dict | None = None) -> TextResponse:
    """Build a fake Scrapy TextResponse from a dict."""
    request = Request(url=url, meta=meta or {})
    return TextResponse(
        url=url,
        body=json.dumps(body).encode("utf-8"),
        encoding="utf-8",
        request=request,
    )


def _collect_items_and_requests(results: Any) -> tuple[list[dict], list[Request]]:
    """Separate yielded items (dicts) from Scrapy Requests."""
    items: list[dict] = []
    requests: list[Request] = []
    for obj in results:
        if isinstance(obj, Request):
            requests.append(obj)
        elif isinstance(obj, dict):
            items.append(obj)
    return items, requests


# ------------------------------------------------------------------
# Fixtures: API responses
# ------------------------------------------------------------------

DEPUTADOS_PAGE_1 = {
    "dados": [
        {
            "id": 204521,
            "nome": "FULANO DA SILVA",
            "nomeCivil": "Fulano Jose da Silva",
            "cpf": "12345678901",
            "siglaPartido": "PT",
            "siglaUf": "SP",
            "idLegislatura": 57,
            "urlFoto": "https://example.com/foto.jpg",
            "email": "fulano@camara.leg.br",
            "dataNascimento": "1980-01-15",
            "sexo": "M",
        },
    ],
    "links": [
        {"rel": "self", "href": "https://dadosabertos.camara.leg.br/api/v2/deputados?pagina=1"},
        {"rel": "next", "href": "https://dadosabertos.camara.leg.br/api/v2/deputados?pagina=2&itens=100&idLegislatura=57"},
    ],
}

DEPUTADOS_PAGE_2 = {
    "dados": [
        {
            "id": 204522,
            "nome": "CICLANA DE SOUZA",
            "siglaPartido": "PL",
            "siglaUf": "RJ",
        },
    ],
    "links": [
        {"rel": "self", "href": "https://dadosabertos.camara.leg.br/api/v2/deputados?pagina=2"},
    ],
}

DESPESAS_RESPONSE = {
    "dados": [
        {
            "ano": 2024,
            "mes": 3,
            "tipoDespesa": "MANUTENÇÃO DE ESCRITÓRIO",
            "valorDocumento": 1500.50,
            "valorLiquido": 1200.00,
            "valorGlosa": 300.50,
            "cnpjCpfFornecedor": "12345678000199",
            "nomeFornecedor": "Empresa ABC Ltda",
            "numDocumento": "NF-001",
            "urlDocumento": "https://example.com/doc.pdf",
        },
    ],
    "links": [],
}

VOTACOES_RESPONSE = {
    "dados": [
        {
            "id": "2345678-90",
            "dataHoraRegistro": "2024-05-10T14:30:00",
            "descricao": "Votação da PEC 123/2024",
            "uriProposicaoPrincipal": "https://dadosabertos.camara.leg.br/api/v2/proposicoes/999",
        },
    ],
    "links": [],
}

VOTOS_RESPONSE = {
    "dados": [
        {
            "deputado_": {"id": 204521, "nome": "FULANO DA SILVA"},
            "tipoVoto": "Sim",
        },
        {
            "deputado_": {"id": 204522, "nome": "CICLANA DE SOUZA"},
            "tipoVoto": "Não",
        },
    ],
    "links": [],
}

VOTOS_PAGE_1 = {
    "dados": [
        {"deputado_": {"id": 1}, "tipoVoto": "Sim"},
    ],
    "links": [
        {"rel": "next", "href": "https://dadosabertos.camara.leg.br/api/v2/votacoes/abc/votos?pagina=2"},
    ],
}

VOTOS_PAGE_2 = {
    "dados": [
        {"deputado_": {"id": 2}, "tipoVoto": "Não"},
    ],
    "links": [],
}

PROPOSICOES_RESPONSE = {
    "dados": [
        {
            "id": 777,
            "siglaTipo": "PL",
            "numero": 123,
            "ano": 2024,
            "ementa": "Dispõe sobre transparência pública",
        },
    ],
    "links": [],
}

FRENTES_RESPONSE = {
    "dados": [
        {"id": 55, "titulo": "Frente Parlamentar da Transparência", "idLegislatura": 57},
        {"id": 56, "titulo": "Frente Parlamentar Digital", "idLegislatura": 57},
    ],
    "links": [],
}

FRENTE_MEMBROS_RESPONSE = {
    "dados": [
        {"id": 204521, "nome": "FULANO DA SILVA"},
        {"id": 204522, "nome": "CICLANA DE SOUZA"},
    ],
}


# ------------------------------------------------------------------
# Tests: Deputados
# ------------------------------------------------------------------


class TestParseDeputados:
    def setup_method(self) -> None:
        self.spider = CamaraDeputadosSpider()

    def test_yields_deputado_items(self) -> None:
        resp = _fake_response(
            "https://dadosabertos.camara.leg.br/api/v2/deputados?pagina=1",
            DEPUTADOS_PAGE_1,
        )
        items, requests = _collect_items_and_requests(self.spider.parse_deputados(resp))

        assert len(items) == 1
        dep = items[0]
        assert dep["_type"] == "deputado"
        assert dep["id"] == 204521
        assert dep["nome"] == "FULANO DA SILVA"
        assert dep["nome_civil"] == "Fulano Jose da Silva"
        assert dep["cpf"] == "12345678901"
        assert dep["sigla_partido"] == "PT"
        assert dep["sigla_uf"] == "SP"
        assert dep["id_legislatura"] == 57
        assert dep["url_foto"] == "https://example.com/foto.jpg"
        assert dep["email"] == "fulano@camara.leg.br"
        assert dep["data_nascimento"] == "1980-01-15"
        assert dep["sexo"] == "M"

    def test_maps_api_field_names_to_snake_case(self) -> None:
        """Verify camelCase -> snake_case field mapping."""
        resp = _fake_response(
            "https://dadosabertos.camara.leg.br/api/v2/deputados?pagina=1",
            DEPUTADOS_PAGE_1,
        )
        items, _ = _collect_items_and_requests(self.spider.parse_deputados(resp))
        dep = items[0]
        # These fields come from camelCase API fields
        assert "sigla_partido" in dep  # from siglaPartido
        assert "sigla_uf" in dep  # from siglaUf
        assert "nome_civil" in dep  # from nomeCivil
        assert "id_legislatura" in dep  # from idLegislatura
        assert "url_foto" in dep  # from urlFoto
        assert "data_nascimento" in dep  # from dataNascimento

    def test_handles_missing_optional_fields(self) -> None:
        resp = _fake_response(
            "https://dadosabertos.camara.leg.br/api/v2/deputados?pagina=1",
            DEPUTADOS_PAGE_2,
        )
        items, _ = _collect_items_and_requests(self.spider.parse_deputados(resp))
        dep = items[0]
        assert dep["id"] == 204522
        assert dep["nome_civil"] is None
        assert dep["cpf"] is None
        assert dep["email"] is None
        assert dep["data_nascimento"] is None
        assert dep["sexo"] is None

    def test_pagination_follows_next_link(self) -> None:
        resp = _fake_response(
            "https://dadosabertos.camara.leg.br/api/v2/deputados?pagina=1",
            DEPUTADOS_PAGE_1,
        )
        _, requests = _collect_items_and_requests(self.spider.parse_deputados(resp))

        # Should have: expense requests (4 years per deputy) + 1 next-page request
        next_page_reqs = [r for r in requests if "pagina=2" in r.url and "despesas" not in r.url]
        assert len(next_page_reqs) == 1
        assert next_page_reqs[0].callback == self.spider.parse_deputados

    def test_no_next_link_stops_pagination(self) -> None:
        resp = _fake_response(
            "https://dadosabertos.camara.leg.br/api/v2/deputados?pagina=2",
            DEPUTADOS_PAGE_2,
        )
        _, requests = _collect_items_and_requests(self.spider.parse_deputados(resp))

        # Only expense requests, no next page
        next_page_reqs = [r for r in requests if "despesas" not in r.url]
        assert len(next_page_reqs) == 0

    def test_spawns_expense_requests_per_deputy(self) -> None:
        resp = _fake_response(
            "https://dadosabertos.camara.leg.br/api/v2/deputados?pagina=1",
            DEPUTADOS_PAGE_1,
        )
        _, requests = _collect_items_and_requests(self.spider.parse_deputados(resp))

        expense_reqs = [r for r in requests if "despesas" in r.url]
        assert len(expense_reqs) == len(CamaraDeputadosSpider.EXPENSE_YEARS)
        for req in expense_reqs:
            assert "204521" in req.url


# ------------------------------------------------------------------
# Tests: Despesas
# ------------------------------------------------------------------


class TestParseDespesas:
    def setup_method(self) -> None:
        self.spider = CamaraDeputadosSpider()

    def test_yields_despesa_items(self) -> None:
        resp = _fake_response(
            "https://dadosabertos.camara.leg.br/api/v2/deputados/204521/despesas?ano=2024&pagina=1",
            DESPESAS_RESPONSE,
        )
        items, _ = _collect_items_and_requests(
            self.spider.parse_despesas(resp, dep_id=204521)
        )

        assert len(items) == 1
        d = items[0]
        assert d["_type"] == "despesa"
        assert d["id_deputado"] == 204521
        assert d["ano"] == 2024
        assert d["mes"] == 3
        assert d["tipo_despesa"] == "MANUTENÇÃO DE ESCRITÓRIO"
        assert d["valor_documento"] == 1500.50
        assert d["valor_liquido"] == 1200.00
        assert d["valor_glosa"] == 300.50
        assert d["cnpj_cpf_fornecedor"] == "12345678000199"
        assert d["nome_fornecedor"] == "Empresa ABC Ltda"
        assert d["numero_documento"] == "NF-001"
        assert d["url_documento"] == "https://example.com/doc.pdf"

    def test_empty_dados_yields_nothing(self) -> None:
        resp = _fake_response(
            "https://dadosabertos.camara.leg.br/api/v2/deputados/204521/despesas?ano=2024&pagina=1",
            {"dados": [], "links": []},
        )
        items, requests = _collect_items_and_requests(
            self.spider.parse_despesas(resp, dep_id=204521)
        )
        assert len(items) == 0
        assert len(requests) == 0


# ------------------------------------------------------------------
# Tests: Votacoes / Votos
# ------------------------------------------------------------------


class TestParseVotacoes:
    def setup_method(self) -> None:
        self.spider = CamaraDeputadosSpider()

    def test_yields_votos_request_per_votacao(self) -> None:
        resp = _fake_response(
            "https://dadosabertos.camara.leg.br/api/v2/votacoes?pagina=1",
            VOTACOES_RESPONSE,
        )
        items, requests = _collect_items_and_requests(self.spider.parse_votacoes(resp))
        assert len(items) == 0  # votacao items come after votos are fetched
        assert len(requests) == 1
        assert "/votos" in requests[0].url

    def test_parse_votos_yields_votacao_item(self) -> None:
        resp = _fake_response(
            "https://dadosabertos.camara.leg.br/api/v2/votacoes/2345678-90/votos?pagina=1",
            VOTOS_RESPONSE,
        )
        items, _ = _collect_items_and_requests(
            self.spider.parse_votos(
                resp,
                id_votacao="2345678-90",
                data="2024-05-10T14:30:00",
                descricao="Votação da PEC 123/2024",
                id_proposicao=999,
            )
        )
        assert len(items) == 1
        v = items[0]
        assert v["_type"] == "votacao"
        assert v["id_votacao"] == "2345678-90"
        assert v["data"] == "2024-05-10T14:30:00"
        assert v["descricao"] == "Votação da PEC 123/2024"
        assert v["id_proposicao"] == 999
        assert len(v["votos"]) == 2
        assert v["votos"][0] == {"id_deputado": 204521, "voto": "Sim"}
        assert v["votos"][1] == {"id_deputado": 204522, "voto": "Não"}

    def test_votos_pagination_accumulates(self) -> None:
        """When votos have multiple pages, the spider accumulates them."""
        resp1 = _fake_response(
            "https://dadosabertos.camara.leg.br/api/v2/votacoes/abc/votos?pagina=1",
            VOTOS_PAGE_1,
        )
        # First page should yield a request (not an item) because there's a next page
        items1, requests1 = _collect_items_and_requests(
            self.spider.parse_votos(
                resp1,
                id_votacao="abc",
                data="2024-01-01T00:00:00",
                descricao="Test vote",
                id_proposicao=None,
            )
        )
        assert len(items1) == 0
        assert len(requests1) == 1
        assert "pagina=2" in requests1[0].url

        # Simulate second page
        resp2 = _fake_response(
            "https://dadosabertos.camara.leg.br/api/v2/votacoes/abc/votos?pagina=2",
            VOTOS_PAGE_2,
        )
        items2, requests2 = _collect_items_and_requests(
            self.spider._parse_votos_continuation(
                resp2,
                id_votacao="abc",
                data="2024-01-01T00:00:00",
                descricao="Test vote",
                id_proposicao=None,
                votos_so_far=[{"id_deputado": 1, "voto": "Sim"}],
            )
        )
        assert len(requests2) == 0
        assert len(items2) == 1
        v = items2[0]
        assert len(v["votos"]) == 2
        assert v["votos"][0]["id_deputado"] == 1
        assert v["votos"][1]["id_deputado"] == 2


# ------------------------------------------------------------------
# Tests: Proposicoes
# ------------------------------------------------------------------


class TestParseProposicoes:
    def setup_method(self) -> None:
        self.spider = CamaraDeputadosSpider()

    def test_yields_proposicao_items(self) -> None:
        resp = _fake_response(
            "https://dadosabertos.camara.leg.br/api/v2/proposicoes?pagina=1",
            PROPOSICOES_RESPONSE,
        )
        items, _ = _collect_items_and_requests(self.spider.parse_proposicoes(resp))
        assert len(items) == 1
        p = items[0]
        assert p["_type"] == "proposicao"
        assert p["id"] == 777
        assert p["tipo"] == "PL"
        assert p["numero"] == 123
        assert p["ano"] == 2024
        assert p["ementa"] == "Dispõe sobre transparência pública"


# ------------------------------------------------------------------
# Tests: Frentes
# ------------------------------------------------------------------


class TestParseFrente:
    def setup_method(self) -> None:
        self.spider = CamaraDeputadosSpider()

    def test_yields_member_requests_per_frente(self) -> None:
        resp = _fake_response(
            "https://dadosabertos.camara.leg.br/api/v2/frentes?idLegislatura=57",
            FRENTES_RESPONSE,
        )
        items, requests = _collect_items_and_requests(self.spider.parse_frentes(resp))
        assert len(items) == 0
        assert len(requests) == 2
        assert "/frentes/55/membros" in requests[0].url
        assert "/frentes/56/membros" in requests[1].url

    def test_parse_frente_membros_yields_item(self) -> None:
        resp = _fake_response(
            "https://dadosabertos.camara.leg.br/api/v2/frentes/55/membros",
            FRENTE_MEMBROS_RESPONSE,
        )
        items, _ = _collect_items_and_requests(
            self.spider.parse_frente_membros(
                resp, frente_id=55, titulo="Frente Parlamentar da Transparência", id_legislatura=57
            )
        )
        assert len(items) == 1
        f = items[0]
        assert f["_type"] == "frente"
        assert f["id"] == 55
        assert f["titulo"] == "Frente Parlamentar da Transparência"
        assert f["id_legislatura"] == 57
        assert f["membros"] == [204521, 204522]


# ------------------------------------------------------------------
# Tests: Helpers
# ------------------------------------------------------------------


class TestHelpers:
    def test_next_link_found(self) -> None:
        spider = CamaraDeputadosSpider()
        data = {"links": [{"rel": "self", "href": "a"}, {"rel": "next", "href": "b"}]}
        assert spider._next_link(data) == "b"

    def test_next_link_missing(self) -> None:
        spider = CamaraDeputadosSpider()
        data = {"links": [{"rel": "self", "href": "a"}]}
        assert spider._next_link(data) is None

    def test_next_link_empty_links(self) -> None:
        spider = CamaraDeputadosSpider()
        assert spider._next_link({"links": []}) is None
        assert spider._next_link({}) is None

    def test_month_end(self) -> None:
        from datetime import date

        assert _month_end(date(2024, 1, 15)) == date(2024, 1, 31)
        assert _month_end(date(2024, 2, 1)) == date(2024, 2, 29)  # leap year
        assert _month_end(date(2023, 2, 1)) == date(2023, 2, 28)
        assert _month_end(date(2024, 12, 5)) == date(2024, 12, 31)

    def test_extract_proposicao_id_from_uri(self) -> None:
        v = {"uriProposicaoPrincipal": "https://example.com/api/v2/proposicoes/999"}
        assert _extract_proposicao_id(v) == 999

    def test_extract_proposicao_id_from_object(self) -> None:
        v = {"proposicaoObjeto": {"id": 42}}
        assert _extract_proposicao_id(v) == 42

    def test_extract_proposicao_id_none(self) -> None:
        assert _extract_proposicao_id({}) is None
        assert _extract_proposicao_id({"uriProposicaoPrincipal": ""}) is None


# ------------------------------------------------------------------
# Tests: start_requests
# ------------------------------------------------------------------


class TestStartRequests:
    def test_start_requests_covers_all_endpoints(self) -> None:
        spider = CamaraDeputadosSpider()
        requests = list(spider.start_requests())

        urls = [r.url for r in requests]
        # Should have at least: 1 deputados + N votacoes months + N proposicoes months + 1 frentes
        assert any("/deputados?" in u for u in urls)
        assert any("/votacoes?" in u for u in urls)
        assert any("/proposicoes?" in u for u in urls)
        assert any("/frentes?" in u for u in urls)

    def test_spider_attributes(self) -> None:
        spider = CamaraDeputadosSpider()
        assert spider.name == "camara_deputados"
        assert spider.source_name == "camara"
        assert "dadosabertos.camara.leg.br" in spider.allowed_domains
