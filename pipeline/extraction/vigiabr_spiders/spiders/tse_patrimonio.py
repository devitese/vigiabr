"""TSE Patrimonio spider — thin Scrapy wrapper over the bulk downloader.

TSE data is distributed as large ZIP file dumps, not via a paginated API.
This spider exists to integrate with the Scrapy scheduling infrastructure
but delegates actual work to the bulk downloader CLI.
"""

from __future__ import annotations

import scrapy


class TsePatrimonioSpider(scrapy.Spider):
    name = "tse_patrimonio"
    source_name = "tse"

    def start_requests(self):
        # Yield a dummy request to satisfy Scrapy's contract
        yield scrapy.Request(
            "https://dadosabertos.tse.jus.br/", callback=self.parse
        )

    def parse(self, response):
        self.logger.info(
            "TSE data collection uses bulk downloader. "
            "Run: python -m bulk.tse_dump_downloader --anos 2018,2022"
        )
