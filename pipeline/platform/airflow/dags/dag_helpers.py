"""Shared helpers for VigiaBR Airflow DAGs."""

from __future__ import annotations

from datetime import datetime, timedelta

DEFAULT_ARGS = {
    "owner": "vigiabr",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(2026, 1, 1),
}

EXTRACTION_CMD = "uv run --project /opt/pipeline/extraction scrapy crawl {spider}"
BULK_DOWNLOAD_CMD = "uv run --project /opt/pipeline/extraction python -m extraction.bulk.{downloader}"
PROCESSING_CMD = "uv run --project /opt/pipeline/processing python -m processing.run {source}"


def extract_cmd(spider: str) -> str:
    return EXTRACTION_CMD.format(spider=spider)


def bulk_cmd(downloader: str) -> str:
    return BULK_DOWNLOAD_CMD.format(downloader=downloader)


def process_cmd(source: str) -> str:
    return PROCESSING_CMD.format(source=source)
