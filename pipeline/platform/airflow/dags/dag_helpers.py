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

_PYPATH = "PYTHONPATH=/opt/pipeline/schemas:/opt/pipeline/extraction:/opt/pipeline/processing"

EXTRACTION_CMD = (
    f"cd /opt/pipeline/extraction && {_PYPATH}"
    " scrapy crawl {spider} -s RAW_OUTPUT_DIR=/opt/pipeline/data/raw"
)
BULK_DOWNLOAD_CMD = f"cd /opt/pipeline/extraction && {_PYPATH} python -m bulk.{{downloader}}"
PROCESSING_CMD = f"{_PYPATH} python -m processing {{source}} --data-dir /opt/pipeline"


def extract_cmd(spider: str) -> str:
    return EXTRACTION_CMD.format(spider=spider)


def bulk_cmd(downloader: str) -> str:
    return BULK_DOWNLOAD_CMD.format(downloader=downloader)


def process_cmd(source: str) -> str:
    return PROCESSING_CMD.format(source=source)
