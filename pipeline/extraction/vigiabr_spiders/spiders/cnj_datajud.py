"""CNJ DataJud spider — public lawsuits from superior courts."""

from __future__ import annotations

import json

import scrapy


class CnjDatajudSpider(scrapy.Spider):
    """Crawl CNJ DataJud API for lawsuit records from superior courts."""

    name = "cnj_datajud"
    source_name = "cnj"
    allowed_domains = ["api-publica.datajud.cnj.jus.br"]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "DOWNLOAD_DELAY": 0.5,
    }

    BASE_URL = "https://api-publica.datajud.cnj.jus.br"
    PAGE_SIZE = 100

    # Superior courts for MVP
    TRIBUNAIS = ["stf", "stj", "tst", "tse", "stm"]

    def start_requests(self):
        for tribunal in self.TRIBUNAIS:
            yield self._build_request(tribunal, search_after=None)

    def _build_request(
        self, tribunal: str, search_after: list | None
    ) -> scrapy.Request:
        url = f"{self.BASE_URL}/api_publica_{tribunal}/_search"
        body: dict = {
            "size": self.PAGE_SIZE,
            "query": {"match_all": {}},
            "sort": [{"dataAjuizamento": {"order": "desc"}}],
        }
        if search_after is not None:
            body["search_after"] = search_after

        return scrapy.Request(
            url=url,
            method="POST",
            body=json.dumps(body),
            headers={"Content-Type": "application/json"},
            callback=self.parse,
            cb_kwargs={"tribunal": tribunal},
            dont_filter=True,
        )

    def parse(self, response, tribunal: str):
        data = json.loads(response.text)
        hits = data.get("hits", {}).get("hits", [])

        if not hits:
            return

        last_sort = None
        for hit in hits:
            source = hit.get("_source", {})
            item = self._parse_processo(source, tribunal)
            if item is not None:
                yield item
            last_sort = hit.get("sort")

        if last_sort is not None and len(hits) == self.PAGE_SIZE:
            yield self._build_request(tribunal, search_after=last_sort)

    def _parse_processo(self, source: dict, tribunal: str) -> dict | None:
        numero_cnj = source.get("numeroProcesso", "")
        if not numero_cnj:
            return None

        classe_obj = source.get("classe", {})
        classe = classe_obj.get("nome", "") if isinstance(classe_obj, dict) else str(classe_obj)

        assuntos_raw = source.get("assuntos", [])
        assuntos = []
        for a in assuntos_raw:
            if isinstance(a, dict):
                nome = a.get("nome", "")
                if nome:
                    assuntos.append(nome)
            elif isinstance(a, str):
                assuntos.append(a)

        orgao = source.get("orgaoJulgador", {})
        vara = orgao.get("nome", None) if isinstance(orgao, dict) else None

        data_ajuizamento = source.get("dataAjuizamento")
        if data_ajuizamento and "T" in str(data_ajuizamento):
            data_ajuizamento = str(data_ajuizamento).split("T")[0]

        situacao = source.get("situacao", None)
        if isinstance(situacao, dict):
            situacao = situacao.get("nome", None)

        valor_causa = source.get("valorCausa")
        if valor_causa is not None:
            try:
                valor_causa = float(valor_causa)
            except (ValueError, TypeError):
                valor_causa = None

        partes = self._parse_partes(source.get("partes", []))

        return {
            "_type": "processo",
            "numero_cnj": numero_cnj,
            "classe": classe,
            "assuntos": assuntos,
            "tribunal": tribunal.upper(),
            "vara": vara,
            "data_ajuizamento": data_ajuizamento,
            "situacao": situacao,
            "valor_causa": valor_causa,
            "partes": partes,
        }

    def _parse_partes(self, partes_raw: list) -> list[dict]:
        """Map DataJud party entries to our contract format."""
        polo_map = {
            "AT": "Autor",
            "PA": "Autor",
            "RE": "Reu",
            "RQ": "Autor",
            "RD": "Reu",
            "TC": "Terceiro",
            "TJ": "Terceiro",
        }

        result = []
        for parte in partes_raw:
            if not isinstance(parte, dict):
                continue
            nome = parte.get("nome", "")
            if not nome:
                continue

            polo = parte.get("polo", "")
            tipo = polo_map.get(polo, "Terceiro")

            cpf_cnpj = parte.get("documento", None)
            if isinstance(cpf_cnpj, list):
                cpf_cnpj = cpf_cnpj[0] if cpf_cnpj else None
            if isinstance(cpf_cnpj, dict):
                cpf_cnpj = cpf_cnpj.get("numero", None)

            result.append({
                "nome": nome,
                "cpf_cnpj": cpf_cnpj,
                "tipo": tipo,
            })
        return result
