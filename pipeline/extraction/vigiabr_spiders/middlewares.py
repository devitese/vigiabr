"""Scrapy downloader middlewares for VigiaBR spiders."""

from __future__ import annotations

import os
from typing import ClassVar

from scrapy import Request, Spider
from scrapy.http import Response


class ApiKeyMiddleware:
    """Inject API keys into request headers based on spider domain."""

    DOMAIN_KEYS: ClassVar[dict[str, tuple[str, str]]] = {
        "api.portaldatransparencia.gov.br": (
            "chave-api-dados",
            "TRANSPARENCIA_API_KEY",
        ),
        "api-publica.datajud.cnj.jus.br": (
            "Authorization",
            "CNJ_DATAJUD_API_KEY",
        ),
    }

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        return middleware

    def process_request(self, request: Request, spider: Spider) -> None:
        from urllib.parse import urlparse

        domain = urlparse(request.url).hostname
        if domain in self.DOMAIN_KEYS:
            header_name, env_var = self.DOMAIN_KEYS[domain]
            api_key = os.environ.get(env_var, "")
            if not api_key:
                spider.logger.warning(
                    "Missing env var %s for domain %s", env_var, domain
                )
                return
            if env_var == "CNJ_DATAJUD_API_KEY":
                request.headers[header_name] = f"APIKey {api_key}"
            else:
                request.headers[header_name] = api_key


class ExponentialBackoffMiddleware:
    """Exponential backoff on 429/5xx responses."""

    MAX_RETRIES = 5
    BASE_DELAY = 2.0

    def process_response(
        self, request: Request, response: Response, spider: Spider
    ) -> Response | Request:
        if response.status not in (429, 500, 502, 503, 504):
            return response

        retry_count = request.meta.get("backoff_retry", 0)
        if retry_count >= self.MAX_RETRIES:
            spider.logger.error(
                "Max retries (%d) exceeded for %s (status %d)",
                self.MAX_RETRIES,
                request.url,
                response.status,
            )
            return response

        delay = self.BASE_DELAY * (2**retry_count)

        # Check Retry-After header
        retry_after = response.headers.get(b"Retry-After")
        if retry_after:
            try:
                delay = max(delay, float(retry_after))
            except (ValueError, TypeError):
                pass

        spider.logger.info(
            "Backoff retry %d/%d for %s (status %d, delay %.1fs)",
            retry_count + 1,
            self.MAX_RETRIES,
            request.url,
            response.status,
            delay,
        )

        new_request = request.copy()
        new_request.meta["backoff_retry"] = retry_count + 1
        new_request.dont_filter = True
        new_request.meta["download_delay"] = delay
        return new_request
