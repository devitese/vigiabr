"""Scrapy item pipelines for VigiaBR spiders."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from scrapy import Spider


class _JSONEncoder(json.JSONEncoder):
    """Handle date, datetime, Decimal serialization."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class JsonlWriterPipeline:
    """Write spider items as JSONL to data/raw/{source}/YYYY-MM-DD/*.jsonl.

    Each spider must set `self.source_name` (e.g., "camara", "senado").
    Items must be dicts or have a `model_dump()` method (Pydantic).
    """

    def __init__(self) -> None:
        self._files: dict[str, Any] = {}
        self._run_date = date.today().isoformat()

    def open_spider(self, spider: Spider) -> None:
        source = getattr(spider, "source_name", spider.name)
        raw_dir = spider.settings.get("RAW_OUTPUT_DIR", "../../data/raw")

        # Resolve relative to the scrapy project root (where scrapy.cfg lives)
        base = Path(spider.settings.get("BASE_DIR", "")).resolve() if spider.settings.get("BASE_DIR") else Path(__file__).resolve().parent.parent
        output_dir = (base / raw_dir / source / self._run_date).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        filepath = output_dir / f"{source}.jsonl"
        self._files[source] = open(filepath, "a", encoding="utf-8")  # noqa: SIM115
        spider.logger.info("JSONL output: %s", filepath)

    def close_spider(self, spider: Spider) -> None:
        source = getattr(spider, "source_name", spider.name)
        fh = self._files.pop(source, None)
        if fh:
            fh.close()

    def process_item(self, item: Any, spider: Spider) -> Any:
        source = getattr(spider, "source_name", spider.name)
        fh = self._files.get(source)
        if fh is None:
            return item

        # Support both dicts and Pydantic models
        if hasattr(item, "model_dump"):
            data = item.model_dump(mode="json")
        elif isinstance(item, dict):
            data = item
        else:
            data = dict(item)

        # Rename 'type' field to '_type' for contract compliance
        if "type" in data and "_type" not in data:
            data["_type"] = data.pop("type")

        line = json.dumps(data, cls=_JSONEncoder, ensure_ascii=False)
        fh.write(line + "\n")
        return item
