"""Scrapy spider for Portal da Transparencia / CGU API.

Source: https://api.portaldatransparencia.gov.br/api-de-dados
Yields: emenda, contrato, ceis, cartao_corporativo
"""

from __future__ import annotations

import scrapy


class TransparenciaCguSpider(scrapy.Spider):
    name = "transparencia_cgu"
    source_name = "transparencia"
    allowed_domains = ["api.portaldatransparencia.gov.br"]

    BASE_URL = "https://api.portaldatransparencia.gov.br/api-de-dados"
    PAGE_SIZE = 15
    EMENDA_YEARS = (2023, 2024, 2025, 2026)

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "DOWNLOAD_DELAY": 0.2,
    }

    def start_requests(self):
        # Emendas — one request per year
        for ano in self.EMENDA_YEARS:
            yield scrapy.Request(
                f"{self.BASE_URL}/emendas?ano={ano}&pagina=1",
                callback=self.parse_emendas,
                cb_kwargs={"ano": ano},
            )

        # Contratos
        yield scrapy.Request(
            f"{self.BASE_URL}/contratos?pagina=1",
            callback=self.parse_contratos,
        )

        # CEIS (sanctioned companies)
        yield scrapy.Request(
            f"{self.BASE_URL}/ceis?pagina=1",
            callback=self.parse_ceis,
        )

        # Cartoes corporativos — crawl by year/month
        for ano in self.EMENDA_YEARS:
            for mes in range(1, 13):
                mm = f"{mes:02d}"
                yield scrapy.Request(
                    f"{self.BASE_URL}/cartoes"
                    f"?mesExtratoInicio={mm}&mesExtratoFim={mm}"
                    f"&anoExtratoInicio={ano}&anoExtratoFim={ano}"
                    f"&pagina=1",
                    callback=self.parse_cartoes,
                )

    # ------------------------------------------------------------------
    # Emendas (parliamentary amendments)
    # ------------------------------------------------------------------

    def parse_emendas(self, response, ano: int):
        data = response.json()
        if not data:
            return

        for record in data:
            autor_obj = record.get("autor") or {}
            autor_nome = (
                autor_obj.get("nome", "") if isinstance(autor_obj, dict) else str(autor_obj)
            )

            yield {
                "_type": "emenda",
                "numero": str(record.get("codigoEmenda", record.get("numero", ""))),
                "autor": autor_nome,
                "tipo": record.get("tipoEmenda") or None,
                "ano": int(record.get("ano", ano)),
                "valor_empenhado": _safe_float(record.get("valorEmpenhado")),
                "valor_pago": _safe_float(record.get("valorPago")) or 0.0,
                "funcao": record.get("funcao") or record.get("nomeFuncao") or None,
                "subfuncao": record.get("subfuncao") or record.get("nomeSubfuncao") or None,
                "beneficiario_nome": _nested_str(record, "beneficiario", "nome"),
                "beneficiario_cnpj_cpf": _nested_str(record, "beneficiario", "codigoFormatado")
                or _nested_str(record, "beneficiario", "cnpjCpf"),
                "localidade": record.get("localidadeDoGasto") or _nested_str(record, "localidade", "nome"),
            }

        # Paginate
        if len(data) >= self.PAGE_SIZE:
            next_page = _next_page_url(response.url)
            yield scrapy.Request(
                next_page,
                callback=self.parse_emendas,
                cb_kwargs={"ano": ano},
            )

    # ------------------------------------------------------------------
    # Contratos (government contracts)
    # ------------------------------------------------------------------

    def parse_contratos(self, response):
        data = response.json()
        if not data:
            return

        for record in data:
            orgao_obj = record.get("unidadeGestora") or record.get("orgao") or {}
            orgao_nome = (
                orgao_obj.get("nome", orgao_obj.get("descricao", ""))
                if isinstance(orgao_obj, dict)
                else str(orgao_obj)
            )

            fornecedor = record.get("fornecedor") or record.get("contratado") or {}

            yield {
                "_type": "contrato",
                "numero": str(record.get("numero", record.get("id", ""))),
                "orgao": orgao_nome,
                "objeto": record.get("objeto") or record.get("objetoContrato") or None,
                "valor": _safe_float(record.get("valorInicial", record.get("valor"))) or 0.0,
                "data_assinatura": record.get("dataAssinatura") or record.get("dataInicioVigencia") or "",
                "data_fim_vigencia": record.get("dataFimVigencia") or record.get("dataTerminoVigencia") or None,
                "cnpj_contratado": (
                    fornecedor.get("cnpjCpf", fornecedor.get("codigoFormatado"))
                    if isinstance(fornecedor, dict)
                    else None
                ),
                "nome_contratado": (
                    fornecedor.get("nome", fornecedor.get("razaoSocial"))
                    if isinstance(fornecedor, dict)
                    else None
                ),
                "modalidade_licitacao": record.get("modalidadeLicitacao") or record.get("modalidadeCompra") or None,
            }

        if len(data) >= self.PAGE_SIZE:
            next_page = _next_page_url(response.url)
            yield scrapy.Request(next_page, callback=self.parse_contratos)

    # ------------------------------------------------------------------
    # CEIS (sanctioned companies registry)
    # ------------------------------------------------------------------

    def parse_ceis(self, response):
        data = response.json()
        if not data:
            return

        for record in data:
            sancionado = record.get("sancionado") or record.get("pessoa") or {}
            orgao = record.get("orgaoSancionador") or {}

            yield {
                "_type": "ceis",
                "cnpj_cpf": (
                    sancionado.get("cnpjCpf", sancionado.get("codigoFormatado", ""))
                    if isinstance(sancionado, dict)
                    else str(sancionado)
                ),
                "nome": (
                    sancionado.get("nome", sancionado.get("razaoSocial", ""))
                    if isinstance(sancionado, dict)
                    else ""
                ),
                "tipo_sancao": record.get("tipoSancao") or record.get("fundamentacaoLegal") or "",
                "orgao_sancionador": (
                    orgao.get("nome", orgao.get("descricao"))
                    if isinstance(orgao, dict)
                    else (orgao or None)
                ),
                "data_inicio": record.get("dataInicioSancao") or record.get("dataInicio") or None,
                "data_fim": record.get("dataFimSancao") or record.get("dataFim") or None,
            }

        if len(data) >= self.PAGE_SIZE:
            next_page = _next_page_url(response.url)
            yield scrapy.Request(next_page, callback=self.parse_ceis)

    # ------------------------------------------------------------------
    # Cartoes corporativos (corporate card expenses)
    # ------------------------------------------------------------------

    def parse_cartoes(self, response):
        data = response.json()
        if not data:
            return

        for record in data:
            portador = record.get("portador") or {}
            estabelecimento = record.get("estabelecimento") or {}

            yield {
                "_type": "cartao_corporativo",
                "cpf_portador": (
                    portador.get("cpf", portador.get("cpfFormatado", ""))
                    if isinstance(portador, dict)
                    else str(portador)
                ),
                "nome_portador": (
                    portador.get("nome", "")
                    if isinstance(portador, dict)
                    else ""
                ),
                "valor": _safe_float(record.get("valorTransacao", record.get("valor"))) or 0.0,
                "data": record.get("dataTransacao") or record.get("data") or "",
                "estabelecimento": (
                    estabelecimento.get("nomeFantasia", estabelecimento.get("nome"))
                    if isinstance(estabelecimento, dict)
                    else (estabelecimento or None)
                ),
                "cnpj_estabelecimento": (
                    estabelecimento.get("cnpj", estabelecimento.get("cnpjFormatado"))
                    if isinstance(estabelecimento, dict)
                    else None
                ),
            }

        if len(data) >= self.PAGE_SIZE:
            next_page = _next_page_url(response.url)
            yield scrapy.Request(next_page, callback=self.parse_cartoes)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _safe_float(value) -> float | None:
    """Convert value to float, handling Brazilian number format.

    Brazilian format: 1.234.567,89 (dot=thousands, comma=decimal).
    """
    if value is None:
        return None
    try:
        s = str(value)
        # If both '.' and ',' are present, treat as Brazilian format
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        return float(s)
    except (ValueError, TypeError):
        return None


def _nested_str(record: dict, *keys: str) -> str | None:
    """Extract a nested string value, returning None if missing."""
    obj = record
    for key in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    if obj is None or (isinstance(obj, str) and not obj.strip()):
        return None
    return str(obj)


def _next_page_url(url: str) -> str:
    """Increment the pagina= query parameter in a URL."""
    import re

    def _increment(match):
        page = int(match.group(1))
        return f"pagina={page + 1}"

    return re.sub(r"pagina=(\d+)", _increment, url, count=1)
