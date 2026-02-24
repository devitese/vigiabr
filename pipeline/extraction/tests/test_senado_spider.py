"""Tests for the Senado Federal spider.

Uses fixture JSON responses to test parsing logic without HTTP calls.
"""

from __future__ import annotations

import json

from scrapy.http import TextResponse, Request

from vigiabr_spiders.spiders.senado_federal import SenadoFederalSpider, _ensure_list


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_response(url: str, body: dict) -> TextResponse:
    """Build a Scrapy TextResponse from a dict (simulates JSON API)."""
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
# Fixtures — realistic Senado API response shapes
# ---------------------------------------------------------------------------

SENATOR_LIST_RESPONSE = {
    "ListaParlamentarEmExercicio": {
        "Metadados": {"Versao": "1"},
        "Parlamentares": {
            "Parlamentar": [
                {
                    "IdentificacaoParlamentar": {
                        "CodigoParlamentar": "5672",
                        "NomeParlamentar": "Alan Rick",
                        "NomeCompletoParlamentar": "Alan Rick Miranda",
                        "SexoParlamentar": "Masculino",
                        "SiglaPartidoParlamentar": "REPUBLICANOS",
                        "UfParlamentar": "AC",
                        "UrlFotoParlamentar": "https://example.com/foto.jpg",
                        "EmailParlamentar": "sen.alanrick@senado.leg.br",
                    },
                    "Mandato": {
                        "CodigoMandato": "596",
                        "PrimeiraLegislaturaDoMandato": {
                            "NumeroLegislatura": "57",
                            "DataInicio": "2023-02-01",
                            "DataFim": "2027-01-31",
                        },
                    },
                },
                {
                    "IdentificacaoParlamentar": {
                        "CodigoParlamentar": "1234",
                        "NomeParlamentar": "Maria Silva",
                        "NomeCompletoParlamentar": "",
                        "SexoParlamentar": "Feminino",
                        "SiglaPartidoParlamentar": "PT",
                        "UfParlamentar": "SP",
                    },
                    "Mandato": {},
                },
            ]
        },
    }
}

# Single senator (not a list) — XML-to-JSON quirk
SENATOR_LIST_SINGLE = {
    "ListaParlamentarEmExercicio": {
        "Parlamentares": {
            "Parlamentar": {
                "IdentificacaoParlamentar": {
                    "CodigoParlamentar": "9999",
                    "NomeParlamentar": "Solo Senator",
                    "SiglaPartidoParlamentar": "PSOL",
                    "UfParlamentar": "RJ",
                },
                "Mandato": {},
            }
        }
    }
}

VOTACAO_RESPONSE = {
    "VotacaoParlamentar": {
        "Parlamentar": {
            "Codigo": "5672",
            "Nome": "Alan Rick",
            "Votacoes": {
                "Votacao": [
                    {
                        "SessaoPlenaria": {
                            "CodigoSessao": "4567",
                            "DataSessao": "2023-03-15",
                        },
                        "Materia": {
                            "Codigo": "155880",
                            "DescricaoIdentificacao": "PEC 2/2023",
                        },
                        "DescricaoVotacao": "Votação da PEC 2/2023",
                        "DescricaoResultado": "Aprovada",
                        "SiglaDescricaoVoto": "Sim",
                    },
                    {
                        "SessaoPlenaria": {
                            "CodigoSessao": "4568",
                            "DataSessao": "2023-03-16",
                        },
                        "Materia": {
                            "Codigo": "155881",
                        },
                        "DescricaoVotacao": "Votação do PL 100/2023",
                        "SiglaDescricaoVoto": "Não",
                    },
                ]
            },
        }
    }
}

# Single vote (not a list)
VOTACAO_SINGLE = {
    "VotacaoParlamentar": {
        "Parlamentar": {
            "Codigo": "5672",
            "Votacoes": {
                "Votacao": {
                    "SessaoPlenaria": {
                        "CodigoSessao": "9000",
                        "DataSessao": "2023-06-01",
                    },
                    "Materia": {"Codigo": "200000"},
                    "DescricaoVotacao": "Votação única",
                    "SiglaDescricaoVoto": "Abstenção",
                }
            },
        }
    }
}

VOTACAO_EMPTY = {
    "VotacaoParlamentar": {
        "Parlamentar": {
            "Codigo": "5672",
            "Votacoes": {},
        }
    }
}

MATERIA_RESPONSE = {
    "ListaMateriasTramitando": {
        "Metadados": {},
        "Materias": {
            "Materia": [
                {
                    "IdentificacaoMateria": {
                        "CodigoMateria": "236",
                        "SiglaSubtipoMateria": "MSG",
                        "NumeroMateria": "00031",
                        "AnoMateria": "1991",
                    },
                    "Ementa": "Encaminha ao Congresso Nacional as Contas",
                    "Autor": "Presidência da República",
                },
                {
                    "IdentificacaoMateria": {
                        "CodigoMateria": "500",
                        "SiglaSubtipoMateria": "PEC",
                        "NumeroMateria": "45",
                        "AnoMateria": "2023",
                    },
                    "Ementa": "Reforma tributária",
                    "SituacaoAtual": "Em tramitação",
                },
            ]
        },
    }
}

# Newer API format: Materias as a top-level list
MATERIA_FLAT_RESPONSE = {
    "Materias": [
        {
            "IdentificacaoMateria": {
                "CodigoMateria": "700",
                "SiglaSubtipoMateria": "PL",
                "NumeroMateria": "10",
                "AnoMateria": "2024",
            },
            "Ementa": "Projeto de lei",
        }
    ]
}

DESPESA_RESPONSE = {
    "DespesasParlamentar": {
        "Parlamentar": {
            "CodigoParlamentar": "5672",
            "Despesas": {
                "Despesa": [
                    {
                        "Ano": "2023",
                        "Mes": "3",
                        "TipoDespesa": "Passagens aéreas",
                        "ValorDespesa": "1234.56",
                        "CnpjCpf": "12345678000100",
                        "Fornecedor": "Airline Corp",
                        "NumeroDocumento": "DOC-001",
                    },
                    {
                        "Ano": "2023",
                        "Mes": "4",
                        "TipoDespesa": "Divulgação",
                        "ValorDespesa": "500,00",
                        "Fornecedor": "Media SA",
                    },
                ]
            },
        }
    }
}

# Single expense (not a list)
DESPESA_SINGLE = {
    "DespesasParlamentar": {
        "Parlamentar": {
            "CodigoParlamentar": "5672",
            "Despesas": {
                "Despesa": {
                    "Ano": "2024",
                    "Mes": "1",
                    "TipoDespesa": "Telefonia",
                    "Valor": "99.90",
                }
            },
        }
    }
}

DESPESA_EMPTY = {
    "DespesasParlamentar": {
        "Parlamentar": {
            "CodigoParlamentar": "5672",
            "Despesas": {},
        }
    }
}


# ---------------------------------------------------------------------------
# Tests — _ensure_list helper
# ---------------------------------------------------------------------------

class TestEnsureList:
    def test_none_returns_empty(self):
        assert _ensure_list(None) == []

    def test_list_passes_through(self):
        assert _ensure_list([1, 2]) == [1, 2]

    def test_dict_wrapped_in_list(self):
        d = {"a": 1}
        assert _ensure_list(d) == [{"a": 1}]

    def test_empty_list_passes_through(self):
        assert _ensure_list([]) == []


# ---------------------------------------------------------------------------
# Tests — Senator list parsing
# ---------------------------------------------------------------------------

class TestParseSenatorList:
    def setup_method(self):
        self.spider = SenadoFederalSpider()

    def test_parses_multiple_senators(self):
        resp = _fake_response(
            "https://legis.senado.leg.br/dadosabertos/senador/lista/atual",
            SENATOR_LIST_RESPONSE,
        )
        items, requests = _collect(self.spider.parse_senator_list(resp))
        senadores = [i for i in items if i["_type"] == "senador"]
        assert len(senadores) == 2

    def test_senator_field_mapping(self):
        resp = _fake_response(
            "https://legis.senado.leg.br/dadosabertos/senador/lista/atual",
            SENATOR_LIST_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_senator_list(resp))
        senadores = [i for i in items if i["_type"] == "senador"]

        s = senadores[0]
        assert s["codigo"] == 5672
        assert s["nome"] == "Alan Rick"
        assert s["nome_completo"] == "Alan Rick Miranda"
        assert s["sexo"] == "Masculino"
        assert s["sigla_partido"] == "REPUBLICANOS"
        assert s["sigla_uf"] == "AC"
        assert s["url_foto"] == "https://example.com/foto.jpg"
        assert s["email"] == "sen.alanrick@senado.leg.br"
        assert s["mandato_inicio"] == "2023-02-01"
        assert s["mandato_fim"] == "2027-01-31"

    def test_empty_fields_become_none(self):
        resp = _fake_response(
            "https://legis.senado.leg.br/dadosabertos/senador/lista/atual",
            SENATOR_LIST_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_senator_list(resp))
        senadores = [i for i in items if i["_type"] == "senador"]

        s = senadores[1]  # Maria Silva — missing many fields
        assert s["nome_completo"] is None  # empty string -> None
        assert s["url_foto"] is None
        assert s["email"] is None
        assert s["mandato_inicio"] is None
        assert s["mandato_fim"] is None

    def test_single_senator_dict_not_list(self):
        """XML-to-JSON can return a single dict instead of a list."""
        resp = _fake_response(
            "https://legis.senado.leg.br/dadosabertos/senador/lista/atual",
            SENATOR_LIST_SINGLE,
        )
        items, requests = _collect(self.spider.parse_senator_list(resp))
        senadores = [i for i in items if i["_type"] == "senador"]
        assert len(senadores) == 1
        assert senadores[0]["codigo"] == 9999
        assert senadores[0]["nome"] == "Solo Senator"

    def test_follow_up_requests_generated(self):
        """Each senator should generate votacao + expense requests."""
        resp = _fake_response(
            "https://legis.senado.leg.br/dadosabertos/senador/lista/atual",
            SENATOR_LIST_RESPONSE,
        )
        items, requests = _collect(self.spider.parse_senator_list(resp))
        # 2 senators => 2 votacao requests + 2 * 4 expense requests = 10
        votacao_reqs = [r for r in requests if "/votacoes" in r.url]
        despesa_reqs = [r for r in requests if "/despesas" in r.url]
        assert len(votacao_reqs) == 2
        assert len(despesa_reqs) == 2 * len(SenadoFederalSpider.EXPENSE_YEARS)


# ---------------------------------------------------------------------------
# Tests — Vote parsing
# ---------------------------------------------------------------------------

class TestParseVotacoes:
    def setup_method(self):
        self.spider = SenadoFederalSpider()

    def test_parses_multiple_votes(self):
        resp = _fake_response(
            "https://legis.senado.leg.br/dadosabertos/senador/5672/votacoes",
            VOTACAO_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_votacoes(resp, codigo_senador=5672))
        assert len(items) == 2
        assert all(i["_type"] == "votacao" for i in items)

    def test_vote_field_mapping(self):
        resp = _fake_response(
            "https://legis.senado.leg.br/dadosabertos/senador/5672/votacoes",
            VOTACAO_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_votacoes(resp, codigo_senador=5672))

        v = items[0]
        assert v["codigo_sessao"] == "4567"
        assert v["data"] == "2023-03-15"
        assert v["descricao"] == "Votação da PEC 2/2023"
        assert v["codigo_materia"] == "155880"
        assert v["resultado"] == "Aprovada"
        assert v["votos"] == [{"codigo_senador": 5672, "voto": "Sim"}]

    def test_missing_resultado_is_none(self):
        resp = _fake_response(
            "https://legis.senado.leg.br/dadosabertos/senador/5672/votacoes",
            VOTACAO_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_votacoes(resp, codigo_senador=5672))
        assert items[1]["resultado"] is None

    def test_single_vote_dict(self):
        resp = _fake_response(
            "https://legis.senado.leg.br/dadosabertos/senador/5672/votacoes",
            VOTACAO_SINGLE,
        )
        items, _ = _collect(self.spider.parse_votacoes(resp, codigo_senador=5672))
        assert len(items) == 1
        assert items[0]["votos"][0]["voto"] == "Abstenção"

    def test_empty_votacoes(self):
        resp = _fake_response(
            "https://legis.senado.leg.br/dadosabertos/senador/5672/votacoes",
            VOTACAO_EMPTY,
        )
        items, _ = _collect(self.spider.parse_votacoes(resp, codigo_senador=5672))
        assert items == []


# ---------------------------------------------------------------------------
# Tests — Materia parsing
# ---------------------------------------------------------------------------

class TestParseMaterias:
    def setup_method(self):
        self.spider = SenadoFederalSpider()

    def test_parses_materias(self):
        resp = _fake_response(
            "https://legis.senado.leg.br/dadosabertos/materia/tramitando",
            MATERIA_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_materias(resp))
        assert len(items) == 2
        assert all(i["_type"] == "materia" for i in items)

    def test_materia_field_mapping(self):
        resp = _fake_response(
            "https://legis.senado.leg.br/dadosabertos/materia/tramitando",
            MATERIA_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_materias(resp))

        m = items[0]
        assert m["codigo"] == "236"
        assert m["tipo"] == "MSG"
        assert m["numero"] == 31
        assert m["ano"] == 1991
        assert m["ementa"] == "Encaminha ao Congresso Nacional as Contas"
        assert m["autor"] == "Presidência da República"
        assert m["situacao"] is None

    def test_materia_with_situacao(self):
        resp = _fake_response(
            "https://legis.senado.leg.br/dadosabertos/materia/tramitando",
            MATERIA_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_materias(resp))
        assert items[1]["situacao"] == "Em tramitação"
        assert items[1]["autor"] is None

    def test_flat_materias_list(self):
        """Newer API may return Materias as a top-level list."""
        resp = _fake_response(
            "https://legis.senado.leg.br/dadosabertos/materia/tramitando",
            MATERIA_FLAT_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_materias(resp))
        assert len(items) == 1
        assert items[0]["codigo"] == "700"
        assert items[0]["tipo"] == "PL"


# ---------------------------------------------------------------------------
# Tests — Expense parsing
# ---------------------------------------------------------------------------

class TestParseDespesas:
    def setup_method(self):
        self.spider = SenadoFederalSpider()

    def test_parses_expenses(self):
        resp = _fake_response(
            "https://legis.senado.leg.br/dadosabertos/senador/5672/despesas?ano=2023",
            DESPESA_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_despesas(resp, codigo_senador=5672))
        assert len(items) == 2
        assert all(i["_type"] == "despesa" for i in items)

    def test_expense_field_mapping(self):
        resp = _fake_response(
            "https://legis.senado.leg.br/dadosabertos/senador/5672/despesas?ano=2023",
            DESPESA_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_despesas(resp, codigo_senador=5672))

        d = items[0]
        assert d["codigo_senador"] == 5672
        assert d["ano"] == 2023
        assert d["mes"] == 3
        assert d["tipo_despesa"] == "Passagens aéreas"
        assert d["valor"] == 1234.56
        assert d["cnpj_cpf"] == "12345678000100"
        assert d["fornecedor"] == "Airline Corp"
        assert d["documento"] == "DOC-001"

    def test_comma_decimal_separator(self):
        """Brazilian locale uses comma as decimal separator."""
        resp = _fake_response(
            "https://legis.senado.leg.br/dadosabertos/senador/5672/despesas?ano=2023",
            DESPESA_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_despesas(resp, codigo_senador=5672))
        assert items[1]["valor"] == 500.0

    def test_missing_optional_fields(self):
        resp = _fake_response(
            "https://legis.senado.leg.br/dadosabertos/senador/5672/despesas?ano=2023",
            DESPESA_RESPONSE,
        )
        items, _ = _collect(self.spider.parse_despesas(resp, codigo_senador=5672))
        d = items[1]
        assert d["cnpj_cpf"] is None
        assert d["documento"] is None

    def test_single_expense_dict(self):
        resp = _fake_response(
            "https://legis.senado.leg.br/dadosabertos/senador/5672/despesas?ano=2024",
            DESPESA_SINGLE,
        )
        items, _ = _collect(self.spider.parse_despesas(resp, codigo_senador=5672))
        assert len(items) == 1
        assert items[0]["valor"] == 99.9
        assert items[0]["tipo_despesa"] == "Telefonia"

    def test_empty_expenses(self):
        resp = _fake_response(
            "https://legis.senado.leg.br/dadosabertos/senador/5672/despesas?ano=2024",
            DESPESA_EMPTY,
        )
        items, _ = _collect(self.spider.parse_despesas(resp, codigo_senador=5672))
        assert items == []


# ---------------------------------------------------------------------------
# Tests — Start requests
# ---------------------------------------------------------------------------

class TestStartRequests:
    def test_generates_initial_requests(self):
        spider = SenadoFederalSpider()
        requests = list(spider.start_requests())
        urls = [r.url for r in requests]
        assert any("senador/lista/atual" in u for u in urls)
        assert any("materia/tramitando" in u for u in urls)
        assert len(requests) == 2
