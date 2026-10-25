"""Ingestion-ready typed records and source provenance metadata."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CitationMetadata:
    """Source provenance for a record; no live registry lookup is implied."""

    source_name: str | None = None
    source_url: str | None = None
    retrieved_at: datetime | None = None
    source_record_id: str | None = None


@dataclass(frozen=True)
class GoodsServices:
    """A goods/services description assigned to a Nice class."""

    nice_class: int | str
    description: str


@dataclass(frozen=True)
class TrademarkRecord:
    """Trademark record supplied by an importer or another upstream service."""

    jurisdiction: str
    goods_services: tuple[GoodsServices, ...]
    citation: CitationMetadata = CitationMetadata()

