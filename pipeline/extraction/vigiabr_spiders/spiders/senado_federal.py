"""Scrapy spider for Senado Federal open data API.

Source: https://legis.senado.leg.br/dadosabertos
Yields: senador, votacao, materia, despesa
"""

from __future__ import annotations

import scrapy


def _ensure_list(obj):
    """Normalize XML-to-JSON quirks: single items come as dicts, not lists."""
    if obj is None:
        return []
    if isinstance(obj, list):
        return obj
    return [obj]


class SenadoFederalSpider(scrapy.Spider):
    name = "senado_federal"
    source_name = "senado"
    allowed_domains = ["legis.senado.leg.br"]

    BASE_URL = "https://legis.senado.leg.br/dadosabertos"
    EXPENSE_YEARS = (2023, 2024, 2025, 2026)

    custom_settings = {
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "application/json",
        },
    }

    def start_requests(self):
        yield scrapy.Request(
            f"{self.BASE_URL}/senador/lista/atual",
            callback=self.parse_senator_list,
        )
        yield scrapy.Request(
            f"{self.BASE_URL}/materia/tramitando",
            callback=self.parse_materias,
        )

    # ------------------------------------------------------------------
    # Senators
    # ------------------------------------------------------------------

    def parse_senator_list(self, response):
        data = response.json()
        parlamentares = (
            data.get("ListaParlamentarEmExercicio", {})
            .get("Parlamentares", {})
            .get("Parlamentar", [])
        )
        for p in _ensure_list(parlamentares):
            id_parl = p.get("IdentificacaoParlamentar", {})
            mandato = p.get("Mandato", {})
            primeira_leg = mandato.get("PrimeiraLegislaturaDoMandato", {})

            codigo = int(id_parl.get("CodigoParlamentar", 0))

            yield {
                "_type": "senador",
                "codigo": codigo,
                "nome": id_parl.get("NomeParlamentar", ""),
                "nome_completo": id_parl.get("NomeCompletoParlamentar") or None,
                "sexo": id_parl.get("SexoParlamentar") or None,
                "sigla_partido": id_parl.get("SiglaPartidoParlamentar", ""),
                "sigla_uf": id_parl.get("UfParlamentar", ""),
                "url_foto": id_parl.get("UrlFotoParlamentar") or None,
                "email": id_parl.get("EmailParlamentar") or None,
                "mandato_inicio": primeira_leg.get("DataInicio") or None,
                "mandato_fim": primeira_leg.get("DataFim") or None,
            }

            # Follow-up requests for this senator
            yield scrapy.Request(
                f"{self.BASE_URL}/senador/{codigo}/votacoes",
                callback=self.parse_votacoes,
                cb_kwargs={"codigo_senador": codigo},
            )
            for ano in self.EXPENSE_YEARS:
                yield scrapy.Request(
                    f"{self.BASE_URL}/senador/{codigo}/despesas?ano={ano}",
                    callback=self.parse_despesas,
                    cb_kwargs={"codigo_senador": codigo},
                    errback=self.handle_error,
                )

    # ------------------------------------------------------------------
    # Votes
    # ------------------------------------------------------------------

    def parse_votacoes(self, response, codigo_senador: int):
        data = response.json()
        parlamentar = data.get("VotacaoParlamentar", {}).get("Parlamentar", {})
        votacoes = (
            parlamentar.get("Votacoes", {}).get("Votacao", [])
        )
        for v in _ensure_list(votacoes):
            sessao = v.get("SessaoPlenaria", {})
            materia = v.get("Materia", {})

            yield {
                "_type": "votacao",
                "codigo_sessao": str(sessao.get("CodigoSessao", v.get("CodigoSessaoVotacao", ""))),
                "data": sessao.get("DataSessao", ""),
                "descricao": v.get("DescricaoVotacao", ""),
                "codigo_materia": str(materia.get("Codigo", "")) or None,
                "resultado": v.get("DescricaoResultado") or None,
                "votos": [
                    {
                        "codigo_senador": codigo_senador,
                        "voto": v.get("SiglaDescricaoVoto", ""),
                    }
                ],
            }

    # ------------------------------------------------------------------
    # Materias (legislative matters)
    # ------------------------------------------------------------------

    def parse_materias(self, response):
        data = response.json()
        # Top-level wrapper varies; try both patterns
        wrapper = data.get("ListaMateriasTramitando", data)
        materias_node = wrapper.get("Materias", {})

        # Newer API may return Materias as a flat list of materia dicts
        if isinstance(materias_node, list):
            materias = materias_node
        else:
            materias = materias_node.get("Materia", [])

        for m in _ensure_list(materias):
            ident = m.get("IdentificacaoMateria", {})
            yield {
                "_type": "materia",
                "codigo": str(ident.get("CodigoMateria", "")),
                "tipo": ident.get("SiglaSubtipoMateria", ""),
                "numero": int(ident.get("NumeroMateria", 0)),
                "ano": int(ident.get("AnoMateria", 0)),
                "ementa": m.get("Ementa") or None,
                "situacao": m.get("SituacaoAtual") or None,
                "autor": m.get("Autor") or None,
            }

    # ------------------------------------------------------------------
    # Expenses (CEAP)
    # ------------------------------------------------------------------

    def parse_despesas(self, response, codigo_senador: int):
        data = response.json()
        # Path: root -> Despesas -> Despesa (list or single)
        despesas_wrapper = data.get("DespesasParlamentar", data)
        parlamentar = despesas_wrapper.get("Parlamentar", {})
        despesas = parlamentar.get("Despesas", {}).get("Despesa", [])

        for d in _ensure_list(despesas):
            valor_str = d.get("ValorDespesa", d.get("Valor", "0"))
            try:
                valor = float(str(valor_str).replace(",", "."))
            except (ValueError, TypeError):
                valor = 0.0

            yield {
                "_type": "despesa",
                "codigo_senador": codigo_senador,
                "ano": int(d.get("Ano", 0)),
                "mes": int(d.get("Mes", 0)),
                "tipo_despesa": d.get("TipoDespesa", ""),
                "valor": valor,
                "cnpj_cpf": d.get("CnpjCpf") or d.get("CNPJCPF") or None,
                "fornecedor": d.get("Fornecedor") or None,
                "documento": d.get("Documento") or d.get("NumeroDocumento") or None,
            }

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    def handle_error(self, failure):
        self.logger.warning("Request failed: %s", failure.request.url)
