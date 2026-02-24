"""Spider for Camara dos Deputados API v2.

Collects deputies, expenses (CEAP), roll-call votes, bills, and
parliamentary fronts from dadosabertos.camara.leg.br.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any, Iterator

import scrapy
from scrapy.http import TextResponse


class CamaraDeputadosSpider(scrapy.Spider):
    name = "camara_deputados"
    source_name = "camara"
    allowed_domains = ["dadosabertos.camara.leg.br"]

    BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
    LEGISLATURE = 57
    EXPENSE_YEARS = (2023, 2024, 2025, 2026)
    DATE_START = date(2023, 2, 1)

    custom_settings = {
        "DOWNLOAD_DELAY": 0.5,
        "DEFAULT_REQUEST_HEADERS": {"Accept": "application/json"},
    }

    def start_requests(self) -> Iterator[scrapy.Request]:
        # 1. Deputies (will also spawn expense requests per deputy)
        yield scrapy.Request(
            f"{self.BASE_URL}/deputados"
            f"?pagina=1&itens=100&idLegislatura={self.LEGISLATURE}",
            callback=self.parse_deputados,
        )

        # 2. Votacoes (month-by-month)
        yield from self._date_range_requests(
            "votacoes", self.parse_votacoes
        )

        # 3. Proposicoes (month-by-month)
        yield from self._date_range_requests(
            "proposicoes", self.parse_proposicoes
        )

        # 4. Frentes
        yield scrapy.Request(
            f"{self.BASE_URL}/frentes?idLegislatura={self.LEGISLATURE}",
            callback=self.parse_frentes,
        )

    # ------------------------------------------------------------------
    # Deputies
    # ------------------------------------------------------------------

    def parse_deputados(self, response: TextResponse) -> Iterator[Any]:
        data = json.loads(response.text)
        for dep in data.get("dados", []):
            dep_id = dep["id"]
            yield {
                "_type": "deputado",
                "id": dep_id,
                "nome": dep.get("nome"),
                "nome_civil": dep.get("nomeCivil"),
                "cpf": dep.get("cpf"),
                "sigla_partido": dep.get("siglaPartido"),
                "sigla_uf": dep.get("siglaUf"),
                "id_legislatura": dep.get("idLegislatura"),
                "url_foto": dep.get("urlFoto"),
                "email": dep.get("email"),
                "data_nascimento": dep.get("dataNascimento"),
                "sexo": dep.get("sexo"),
            }
            # Enqueue expense requests for this deputy
            for ano in self.EXPENSE_YEARS:
                yield scrapy.Request(
                    f"{self.BASE_URL}/deputados/{dep_id}/despesas"
                    f"?ano={ano}&pagina=1&itens=100",
                    callback=self.parse_despesas,
                    cb_kwargs={"dep_id": dep_id},
                )

        next_url = self._next_link(data)
        if next_url:
            yield scrapy.Request(next_url, callback=self.parse_deputados)

    # ------------------------------------------------------------------
    # Expenses (CEAP)
    # ------------------------------------------------------------------

    def parse_despesas(self, response: TextResponse, dep_id: int) -> Iterator[Any]:
        data = json.loads(response.text)
        for d in data.get("dados", []):
            yield {
                "_type": "despesa",
                "id_deputado": dep_id,
                "ano": d.get("ano"),
                "mes": d.get("mes"),
                "tipo_despesa": d.get("tipoDespesa"),
                "valor_documento": d.get("valorDocumento"),
                "valor_liquido": d.get("valorLiquido"),
                "valor_glosa": d.get("valorGlosa"),
                "cnpj_cpf_fornecedor": d.get("cnpjCpfFornecedor"),
                "nome_fornecedor": d.get("nomeFornecedor"),
                "numero_documento": d.get("numDocumento"),
                "url_documento": d.get("urlDocumento"),
            }

        next_url = self._next_link(data)
        if next_url:
            yield scrapy.Request(
                next_url,
                callback=self.parse_despesas,
                cb_kwargs={"dep_id": dep_id},
            )

    # ------------------------------------------------------------------
    # Roll-call votes
    # ------------------------------------------------------------------

    def parse_votacoes(self, response: TextResponse) -> Iterator[Any]:
        data = json.loads(response.text)
        for v in data.get("dados", []):
            vot_id = v.get("id")
            yield scrapy.Request(
                f"{self.BASE_URL}/votacoes/{vot_id}/votos"
                f"?pagina=1&itens=100",
                callback=self.parse_votos,
                cb_kwargs={
                    "id_votacao": str(vot_id),
                    "data": v.get("dataHoraRegistro") or v.get("data", ""),
                    "descricao": v.get("descricao", ""),
                    "id_proposicao": _extract_proposicao_id(v),
                },
            )

        next_url = self._next_link(data)
        if next_url:
            yield scrapy.Request(next_url, callback=self.parse_votacoes)

    def parse_votos(
        self,
        response: TextResponse,
        id_votacao: str,
        data: str,
        descricao: str,
        id_proposicao: int | None,
    ) -> Iterator[Any]:
        resp_data = json.loads(response.text)
        votos = _extract_votos(resp_data)

        next_url = self._next_link(resp_data)
        if next_url:
            yield scrapy.Request(
                next_url,
                callback=self._parse_votos_continuation,
                cb_kwargs={
                    "id_votacao": id_votacao,
                    "data": data,
                    "descricao": descricao,
                    "id_proposicao": id_proposicao,
                    "votos_so_far": votos,
                },
            )
        else:
            yield {
                "_type": "votacao",
                "id_votacao": id_votacao,
                "data": data,
                "descricao": descricao,
                "id_proposicao": id_proposicao,
                "votos": votos,
            }

    def _parse_votos_continuation(
        self,
        response: TextResponse,
        id_votacao: str,
        data: str,
        descricao: str,
        id_proposicao: int | None,
        votos_so_far: list[dict],
    ) -> Iterator[Any]:
        resp_data = json.loads(response.text)
        votos_so_far.extend(_extract_votos(resp_data))

        next_url = self._next_link(resp_data)
        if next_url:
            yield scrapy.Request(
                next_url,
                callback=self._parse_votos_continuation,
                cb_kwargs={
                    "id_votacao": id_votacao,
                    "data": data,
                    "descricao": descricao,
                    "id_proposicao": id_proposicao,
                    "votos_so_far": votos_so_far,
                },
            )
        else:
            yield {
                "_type": "votacao",
                "id_votacao": id_votacao,
                "data": data,
                "descricao": descricao,
                "id_proposicao": id_proposicao,
                "votos": votos_so_far,
            }

    # ------------------------------------------------------------------
    # Propositions (bills)
    # ------------------------------------------------------------------

    def parse_proposicoes(self, response: TextResponse) -> Iterator[Any]:
        data = json.loads(response.text)
        for p in data.get("dados", []):
            yield {
                "_type": "proposicao",
                "id": p.get("id"),
                "tipo": p.get("siglaTipo"),
                "numero": p.get("numero"),
                "ano": p.get("ano"),
                "ementa": p.get("ementa"),
                "situacao": None,
                "tema": None,
                "id_autor": None,
            }

        next_url = self._next_link(data)
        if next_url:
            yield scrapy.Request(next_url, callback=self.parse_proposicoes)

    # ------------------------------------------------------------------
    # Parliamentary fronts (frentes)
    # ------------------------------------------------------------------

    def parse_frentes(self, response: TextResponse) -> Iterator[Any]:
        data = json.loads(response.text)
        for f in data.get("dados", []):
            frente_id = f.get("id")
            yield scrapy.Request(
                f"{self.BASE_URL}/frentes/{frente_id}/membros",
                callback=self.parse_frente_membros,
                cb_kwargs={
                    "frente_id": frente_id,
                    "titulo": f.get("titulo", ""),
                    "id_legislatura": f.get("idLegislatura"),
                },
            )

    def parse_frente_membros(
        self,
        response: TextResponse,
        frente_id: int,
        titulo: str,
        id_legislatura: int | None,
    ) -> Iterator[Any]:
        data = json.loads(response.text)
        membros = [m.get("id") for m in data.get("dados", []) if m.get("id")]
        yield {
            "_type": "frente",
            "id": frente_id,
            "titulo": titulo,
            "id_legislatura": id_legislatura,
            "membros": membros,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _date_range_requests(
        self, endpoint: str, callback: Any
    ) -> Iterator[scrapy.Request]:
        """Generate month-by-month paginated requests for a date-ranged endpoint."""
        current = self.DATE_START
        today = date.today()
        while current < today:
            end = _month_end(current)
            if end > today:
                end = today
            yield scrapy.Request(
                f"{self.BASE_URL}/{endpoint}"
                f"?dataInicio={current.isoformat()}"
                f"&dataFim={end.isoformat()}"
                f"&pagina=1&itens=100",
                callback=callback,
            )
            current = end + timedelta(days=1)

    @staticmethod
    def _next_link(data: dict) -> str | None:
        """Extract the 'next' pagination URL from the API response links."""
        for link in data.get("links", []):
            if link.get("rel") == "next":
                return link.get("href")
        return None


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _month_end(d: date) -> date:
    """Return the last day of the month for the given date."""
    if d.month == 12:
        return date(d.year, 12, 31)
    return date(d.year, d.month + 1, 1) - timedelta(days=1)


def _extract_proposicao_id(votacao: dict) -> int | None:
    """Try to extract a proposicao ID from the votacao object."""
    obj = votacao.get("proposicaoObjeto")
    if isinstance(obj, dict):
        return obj.get("id")
    uri = votacao.get("uriProposicaoPrincipal", "")
    if uri:
        parts = uri.rstrip("/").split("/")
        try:
            return int(parts[-1])
        except (ValueError, IndexError):
            pass
    return None


def _extract_votos(resp_data: dict) -> list[dict]:
    """Parse the votos array from a /votacoes/{id}/votos response."""
    votos = []
    for voto in resp_data.get("dados", []):
        deputado = voto.get("deputado_", {})
        votos.append(
            {
                "id_deputado": deputado.get("id"),
                "voto": voto.get("tipoVoto"),
            }
        )
    return votos
