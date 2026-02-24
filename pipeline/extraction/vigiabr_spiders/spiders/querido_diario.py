"""Querido Diario spider — federal gazette entries from OKBR API."""

from __future__ import annotations

import json
import re
from urllib.parse import urlencode

import scrapy


class QueridoDiarioSpider(scrapy.Spider):
    """Crawl Querido Diario API for federal gazette entries about appointments."""

    name = "querido_diario"
    source_name = "querido_diario"
    allowed_domains = ["api.queridodiario.ok.org.br"]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
    }

    BASE_URL = "https://api.queridodiario.ok.org.br"
    PAGE_SIZE = 100

    SEARCH_TERMS = [
        "nomeação",
        "exoneração",
        "DAS",
        "cargo em comissão",
    ]

    def start_requests(self):
        for term in self.SEARCH_TERMS:
            yield self._build_request(term, offset=0)

    def _build_request(self, term: str, offset: int) -> scrapy.Request:
        params = {
            "querystring": term,
            "size": self.PAGE_SIZE,
            "offset": offset,
            "sort_by": "descending_date",
        }
        url = f"{self.BASE_URL}/gazettes?{urlencode(params)}"
        return scrapy.Request(
            url=url,
            callback=self.parse,
            cb_kwargs={"term": term, "offset": offset},
            dont_filter=True,
        )

    def parse(self, response, term: str, offset: int):
        data = json.loads(response.text)
        gazettes = data.get("gazettes", [])
        total = data.get("total_gazettes", 0)

        if not gazettes:
            return

        for gazette in gazettes:
            yield from self._parse_gazette(gazette)

        next_offset = offset + self.PAGE_SIZE
        if next_offset < total:
            yield self._build_request(term, next_offset)

    def _parse_gazette(self, gazette: dict):
        date_str = gazette.get("date", "")
        edition = gazette.get("edition", None)
        section = gazette.get("section", None)
        url = gazette.get("url", None)
        excerpts = gazette.get("excerpts", [])
        full_text = "\n".join(excerpts) if excerpts else gazette.get("txt_url", "")

        entities = self._extract_entities(full_text)

        yield {
            "_type": "publicacao",
            "data_publicacao": date_str,
            "edicao_dou": edition,
            "secao_dou": section,
            "texto": full_text,
            "url_fonte": url,
            "entidades_mencionadas": entities,
        }

        yield from self._extract_nomeacoes(full_text, date_str, edition, section, url)

    def _extract_entities(self, text: str) -> list[str]:
        """Extract entity names from text using simple capitalized-word heuristic."""
        if not text:
            return []
        # Match sequences of capitalized words (2+ words, likely proper names)
        pattern = r"\b([A-Z][a-záàâãéèêíïóôõúüç]+ (?:(?:de|da|do|dos|das|e) )*[A-Z][a-záàâãéèêíïóôõúüç]+(?:\s[A-Z][a-záàâãéèêíïóôõúüç]+)*)\b"
        matches = re.findall(pattern, text)
        return list(dict.fromkeys(matches))  # dedupe preserving order

    def _extract_nomeacoes(
        self, text: str, date_str: str, edition: str | None, section: str | None, url: str | None
    ):
        """Basic pattern extraction for appointment items. MVP-level, will be replaced by NLP."""
        if not text:
            return

        tipo_map = {
            "NOMEAR": "Nomeacao",
            "NOMEAÇÃO": "Nomeacao",
            "EXONERAR": "Exoneracao",
            "EXONERAÇÃO": "Exoneracao",
            "SUBSTITUIÇÃO": "Substituicao",
            "SUBSTITUIR": "Substituicao",
        }

        # Pattern: NOMEAR/EXONERAR ... <NAME> ... para/do cargo de <CARGO>
        pattern = (
            r"(?P<tipo>NOMEAR|EXONERAR|NOMEAÇÃO|EXONERAÇÃO|SUBSTITUIÇÃO|SUBSTITUIR)"
            r"[,\s]+(?P<nome>[A-Z][A-ZÀ-Ú\s]+?)"
            r"[,\s]+(?:para|do|no)\s+cargo\s+(?:de\s+)?(?P<cargo>[^,\.\n]+)"
        )
        for match in re.finditer(pattern, text, re.IGNORECASE):
            nome = match.group("nome").strip()
            cargo = match.group("cargo").strip()
            tipo_raw = match.group("tipo").upper()
            tipo = tipo_map.get(tipo_raw)

            # Check if it's a DAS position
            if re.search(r"\bDAS\b", cargo, re.IGNORECASE):
                tipo = "DAS"

            yield {
                "_type": "nomeacao",
                "nome": nome,
                "cpf": None,
                "cargo": cargo,
                "tipo": tipo,
                "orgao": None,
                "data_publicacao": date_str,
                "edicao_dou": edition,
                "secao_dou": section,
                "url_fonte": url,
            }
