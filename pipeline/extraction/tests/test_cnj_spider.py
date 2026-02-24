"""Tests for the CNJ DataJud spider."""

from __future__ import annotations

import json

from scrapy.http import TextResponse, Request

from vigiabr_spiders.spiders.cnj_datajud import CnjDatajudSpider


def _fake_response(
    body: dict,
    url: str = "https://api-publica.datajud.cnj.jus.br/api_publica_stf/_search",
) -> TextResponse:
    return TextResponse(
        url=url,
        body=json.dumps(body).encode("utf-8"),
        encoding="utf-8",
        request=Request(url=url, method="POST"),
    )


def _spider() -> CnjDatajudSpider:
    return CnjDatajudSpider()


def _make_hit(
    numero: str = "0000001-23.2024.1.00.0001",
    classe: str = "Ação Civil Pública",
    tribunal: str = "STF",
    sort_values: list | None = None,
    **overrides,
) -> dict:
    source = {
        "numeroProcesso": numero,
        "classe": {"nome": classe},
        "assuntos": [{"nome": "Direito Constitucional"}],
        "orgaoJulgador": {"nome": "1ª Turma"},
        "dataAjuizamento": "2024-01-15T00:00:00.000Z",
        "situacao": {"nome": "Em andamento"},
        "valorCausa": 10000.50,
        "partes": [
            {"nome": "Ministério Público Federal", "polo": "AT", "documento": None},
            {"nome": "Fulano de Tal", "polo": "RE", "documento": "12345678901"},
        ],
        **overrides,
    }
    return {
        "_source": source,
        "sort": sort_values or [1705276800000],
    }


class TestStartRequests:
    def test_generates_one_request_per_tribunal(self):
        spider = _spider()
        requests = list(spider.start_requests())
        assert len(requests) == len(spider.TRIBUNAIS)

    def test_uses_post_method(self):
        spider = _spider()
        requests = list(spider.start_requests())
        for req in requests:
            assert req.method == "POST"

    def test_urls_contain_tribunal_alias(self):
        spider = _spider()
        requests = list(spider.start_requests())
        for tribunal, req in zip(spider.TRIBUNAIS, requests):
            assert f"api_publica_{tribunal}" in req.url

    def test_request_body_has_match_all_query(self):
        spider = _spider()
        requests = list(spider.start_requests())
        for req in requests:
            body = json.loads(req.body)
            assert body["query"] == {"match_all": {}}
            assert body["size"] == 100
            assert "search_after" not in body


class TestParse:
    def test_yields_processo_items(self):
        spider = _spider()
        body = {
            "hits": {
                "hits": [_make_hit()],
            }
        }
        response = _fake_response(body)
        items = list(spider.parse(response, tribunal="stf"))

        processos = [i for i in items if isinstance(i, dict)]
        assert len(processos) == 1
        proc = processos[0]
        assert proc["_type"] == "processo"
        assert proc["numero_cnj"] == "0000001-23.2024.1.00.0001"
        assert proc["classe"] == "Ação Civil Pública"
        assert proc["tribunal"] == "STF"
        assert proc["vara"] == "1ª Turma"
        assert proc["data_ajuizamento"] == "2024-01-15"
        assert proc["situacao"] == "Em andamento"
        assert proc["valor_causa"] == 10000.50

    def test_assuntos_extraction(self):
        spider = _spider()
        hit = _make_hit(
            assuntos=[
                {"nome": "Direito Constitucional"},
                {"nome": "Controle de Constitucionalidade"},
            ]
        )
        body = {"hits": {"hits": [hit]}}
        response = _fake_response(body)
        items = [i for i in spider.parse(response, tribunal="stf") if isinstance(i, dict)]
        assert items[0]["assuntos"] == [
            "Direito Constitucional",
            "Controle de Constitucionalidade",
        ]

    def test_partes_mapping(self):
        spider = _spider()
        hit = _make_hit(
            partes=[
                {"nome": "MPF", "polo": "AT", "documento": None},
                {"nome": "Réu Silva", "polo": "RE", "documento": "12345678901"},
                {"nome": "Terceiro Interessado", "polo": "TC", "documento": None},
            ]
        )
        body = {"hits": {"hits": [hit]}}
        response = _fake_response(body)
        items = [i for i in spider.parse(response, tribunal="stj") if isinstance(i, dict)]
        partes = items[0]["partes"]
        assert len(partes) == 3
        assert partes[0]["tipo"] == "Autor"
        assert partes[1]["tipo"] == "Reu"
        assert partes[1]["cpf_cnpj"] == "12345678901"
        assert partes[2]["tipo"] == "Terceiro"

    def test_empty_hits_stops(self):
        spider = _spider()
        body = {"hits": {"hits": []}}
        response = _fake_response(body)
        items = list(spider.parse(response, tribunal="stf"))
        assert items == []

    def test_skips_hit_without_numero(self):
        spider = _spider()
        hit = _make_hit()
        hit["_source"]["numeroProcesso"] = ""
        body = {"hits": {"hits": [hit]}}
        response = _fake_response(body)
        items = [i for i in spider.parse(response, tribunal="stf") if isinstance(i, dict)]
        assert len(items) == 0


class TestPagination:
    def test_generates_next_request_with_search_after(self):
        spider = _spider()
        hits = [_make_hit(sort_values=[1705276800000 - i]) for i in range(100)]
        body = {"hits": {"hits": hits}}
        response = _fake_response(body)
        results = list(spider.parse(response, tribunal="stf"))

        requests = [r for r in results if hasattr(r, "url")]
        assert len(requests) == 1

        next_body = json.loads(requests[0].body)
        assert "search_after" in next_body
        assert next_body["search_after"] == hits[-1]["sort"]

    def test_no_next_page_when_fewer_than_page_size(self):
        spider = _spider()
        hits = [_make_hit(sort_values=[1705276800000 - i]) for i in range(50)]
        body = {"hits": {"hits": hits}}
        response = _fake_response(body)
        results = list(spider.parse(response, tribunal="stf"))

        requests = [r for r in results if hasattr(r, "url")]
        assert len(requests) == 0


class TestEdgeCases:
    def test_classe_as_string(self):
        spider = _spider()
        hit = _make_hit(classe="Mandado de Segurança")
        # Override with string instead of dict
        hit["_source"]["classe"] = "Mandado de Segurança"
        body = {"hits": {"hits": [hit]}}
        response = _fake_response(body)
        items = [i for i in spider.parse(response, tribunal="stf") if isinstance(i, dict)]
        assert items[0]["classe"] == "Mandado de Segurança"

    def test_situacao_as_string(self):
        spider = _spider()
        hit = _make_hit()
        hit["_source"]["situacao"] = "Finalizado"
        body = {"hits": {"hits": [hit]}}
        response = _fake_response(body)
        items = [i for i in spider.parse(response, tribunal="stf") if isinstance(i, dict)]
        assert items[0]["situacao"] == "Finalizado"

    def test_valor_causa_none(self):
        spider = _spider()
        hit = _make_hit()
        hit["_source"]["valorCausa"] = None
        body = {"hits": {"hits": [hit]}}
        response = _fake_response(body)
        items = [i for i in spider.parse(response, tribunal="stf") if isinstance(i, dict)]
        assert items[0]["valor_causa"] is None

    def test_valor_causa_invalid(self):
        spider = _spider()
        hit = _make_hit()
        hit["_source"]["valorCausa"] = "not_a_number"
        body = {"hits": {"hits": [hit]}}
        response = _fake_response(body)
        items = [i for i in spider.parse(response, tribunal="stf") if isinstance(i, dict)]
        assert items[0]["valor_causa"] is None

    def test_partes_with_document_as_list(self):
        spider = _spider()
        hit = _make_hit(
            partes=[
                {"nome": "Autor X", "polo": "AT", "documento": ["111.222.333-44"]},
            ]
        )
        body = {"hits": {"hits": [hit]}}
        response = _fake_response(body)
        items = [i for i in spider.parse(response, tribunal="stf") if isinstance(i, dict)]
        assert items[0]["partes"][0]["cpf_cnpj"] == "111.222.333-44"

    def test_partes_with_document_as_dict(self):
        spider = _spider()
        hit = _make_hit(
            partes=[
                {"nome": "Autor Y", "polo": "AT", "documento": {"numero": "99988877766"}},
            ]
        )
        body = {"hits": {"hits": [hit]}}
        response = _fake_response(body)
        items = [i for i in spider.parse(response, tribunal="stf") if isinstance(i, dict)]
        assert items[0]["partes"][0]["cpf_cnpj"] == "99988877766"

    def test_assuntos_as_strings(self):
        spider = _spider()
        hit = _make_hit(assuntos=["Direito Penal", "Crime contra a administração"])
        body = {"hits": {"hits": [hit]}}
        response = _fake_response(body)
        items = [i for i in spider.parse(response, tribunal="stf") if isinstance(i, dict)]
        assert items[0]["assuntos"] == ["Direito Penal", "Crime contra a administração"]

    def test_missing_orgao_julgador(self):
        spider = _spider()
        hit = _make_hit()
        del hit["_source"]["orgaoJulgador"]
        body = {"hits": {"hits": [hit]}}
        response = _fake_response(body)
        items = [i for i in spider.parse(response, tribunal="stf") if isinstance(i, dict)]
        assert items[0]["vara"] is None

    def test_empty_partes_list(self):
        spider = _spider()
        hit = _make_hit(partes=[])
        body = {"hits": {"hits": [hit]}}
        response = _fake_response(body)
        items = [i for i in spider.parse(response, tribunal="stf") if isinstance(i, dict)]
        assert items[0]["partes"] == []
