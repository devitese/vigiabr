"""Tests for the Querido Diario spider."""

from __future__ import annotations

import json

from scrapy.http import TextResponse, Request

from vigiabr_spiders.spiders.querido_diario import QueridoDiarioSpider


def _fake_response(body: dict, url: str = "https://api.queridodiario.ok.org.br/gazettes") -> TextResponse:
    return TextResponse(
        url=url,
        body=json.dumps(body).encode("utf-8"),
        encoding="utf-8",
        request=Request(url=url),
    )


def _spider() -> QueridoDiarioSpider:
    return QueridoDiarioSpider()


class TestStartRequests:
    def test_generates_one_request_per_search_term(self):
        spider = _spider()
        requests = list(spider.start_requests())
        assert len(requests) == len(spider.SEARCH_TERMS)

    def test_requests_target_gazettes_endpoint(self):
        spider = _spider()
        requests = list(spider.start_requests())
        for req in requests:
            assert "/gazettes?" in req.url

    def test_first_request_has_offset_zero(self):
        spider = _spider()
        requests = list(spider.start_requests())
        for req in requests:
            assert "offset=0" in req.url


class TestParse:
    def test_yields_publicacao_items(self):
        spider = _spider()
        body = {
            "total_gazettes": 1,
            "gazettes": [
                {
                    "date": "2024-01-15",
                    "edition": "12",
                    "section": "2",
                    "url": "https://example.com/gazette/1",
                    "excerpts": ["NOMEAR Fulano de Tal para cargo de Assessor"],
                    "territory_name": "Brasilia",
                }
            ],
        }
        response = _fake_response(body)
        items = list(spider.parse(response, term="nomeação", offset=0))

        publicacoes = [i for i in items if isinstance(i, dict) and i.get("_type") == "publicacao"]
        assert len(publicacoes) == 1
        pub = publicacoes[0]
        assert pub["data_publicacao"] == "2024-01-15"
        assert pub["edicao_dou"] == "12"
        assert pub["secao_dou"] == "2"
        assert "NOMEAR" in pub["texto"]
        assert pub["url_fonte"] == "https://example.com/gazette/1"

    def test_yields_nomeacao_items_from_text(self):
        spider = _spider()
        body = {
            "total_gazettes": 1,
            "gazettes": [
                {
                    "date": "2024-01-15",
                    "excerpts": [
                        "NOMEAR JOAO DA SILVA, para cargo de Assessor Especial"
                    ],
                }
            ],
        }
        response = _fake_response(body)
        items = list(spider.parse(response, term="nomeação", offset=0))

        nomeacoes = [i for i in items if isinstance(i, dict) and i.get("_type") == "nomeacao"]
        assert len(nomeacoes) == 1
        nom = nomeacoes[0]
        assert nom["nome"] == "JOAO DA SILVA"
        assert nom["cargo"] == "Assessor Especial"
        assert nom["tipo"] == "Nomeacao"
        assert nom["cpf"] is None

    def test_das_type_detected(self):
        spider = _spider()
        body = {
            "total_gazettes": 1,
            "gazettes": [
                {
                    "date": "2024-03-10",
                    "excerpts": [
                        "NOMEAR MARIA OLIVEIRA, para cargo de DAS-5 Diretor"
                    ],
                }
            ],
        }
        response = _fake_response(body)
        items = list(spider.parse(response, term="DAS", offset=0))

        nomeacoes = [i for i in items if isinstance(i, dict) and i.get("_type") == "nomeacao"]
        assert len(nomeacoes) == 1
        assert nomeacoes[0]["tipo"] == "DAS"

    def test_exoneracao_type(self):
        spider = _spider()
        body = {
            "total_gazettes": 1,
            "gazettes": [
                {
                    "date": "2024-02-20",
                    "excerpts": [
                        "EXONERAR CARLOS SANTOS, do cargo de Coordenador Geral"
                    ],
                }
            ],
        }
        response = _fake_response(body)
        items = list(spider.parse(response, term="exoneração", offset=0))

        nomeacoes = [i for i in items if isinstance(i, dict) and i.get("_type") == "nomeacao"]
        assert len(nomeacoes) == 1
        assert nomeacoes[0]["tipo"] == "Exoneracao"
        assert nomeacoes[0]["nome"] == "CARLOS SANTOS"

    def test_empty_gazette_list_stops(self):
        spider = _spider()
        body = {"total_gazettes": 0, "gazettes": []}
        response = _fake_response(body)
        items = list(spider.parse(response, term="nomeação", offset=0))
        assert items == []

    def test_entities_extracted(self):
        spider = _spider()
        body = {
            "total_gazettes": 1,
            "gazettes": [
                {
                    "date": "2024-01-15",
                    "excerpts": ["Maria Silva foi nomeada pelo Ministro João Pereira"],
                }
            ],
        }
        response = _fake_response(body)
        items = list(spider.parse(response, term="nomeação", offset=0))
        publicacoes = [i for i in items if isinstance(i, dict) and i.get("_type") == "publicacao"]
        assert len(publicacoes) == 1
        entities = publicacoes[0]["entidades_mencionadas"]
        assert isinstance(entities, list)


class TestPagination:
    def test_pagination_generates_next_request(self):
        spider = _spider()
        body = {
            "total_gazettes": 250,
            "gazettes": [
                {"date": "2024-01-15", "excerpts": ["text"]}
                for _ in range(100)
            ],
        }
        response = _fake_response(body)
        results = list(spider.parse(response, term="nomeação", offset=0))

        requests = [r for r in results if hasattr(r, "url")]
        assert len(requests) == 1
        assert "offset=100" in requests[0].url

    def test_no_next_page_when_offset_exceeds_total(self):
        spider = _spider()
        body = {
            "total_gazettes": 50,
            "gazettes": [
                {"date": "2024-01-15", "excerpts": ["text"]}
                for _ in range(50)
            ],
        }
        response = _fake_response(body)
        results = list(spider.parse(response, term="nomeação", offset=0))

        requests = [r for r in results if hasattr(r, "url")]
        assert len(requests) == 0


class TestEdgeCases:
    def test_gazette_without_excerpts(self):
        spider = _spider()
        body = {
            "total_gazettes": 1,
            "gazettes": [
                {"date": "2024-01-15"},
            ],
        }
        response = _fake_response(body)
        items = list(spider.parse(response, term="nomeação", offset=0))
        publicacoes = [i for i in items if isinstance(i, dict) and i.get("_type") == "publicacao"]
        assert len(publicacoes) == 1
        assert publicacoes[0]["texto"] == ""

    def test_gazette_with_none_fields(self):
        spider = _spider()
        body = {
            "total_gazettes": 1,
            "gazettes": [
                {
                    "date": "2024-01-15",
                    "edition": None,
                    "section": None,
                    "url": None,
                    "excerpts": ["some text"],
                }
            ],
        }
        response = _fake_response(body)
        items = list(spider.parse(response, term="nomeação", offset=0))
        publicacoes = [i for i in items if isinstance(i, dict) and i.get("_type") == "publicacao"]
        assert len(publicacoes) == 1
        pub = publicacoes[0]
        assert pub["edicao_dou"] is None
        assert pub["secao_dou"] is None
        assert pub["url_fonte"] is None
