"""Typed, deterministic jurisdiction-aware trademark matching primitives."""

from .matcher import (
    ConflictRanking,
    MatchDisposition,
    MatchResult,
    compare_records,
    normalize_jurisdiction,
    normalize_nice_class,
)
from .models import CitationMetadata, GoodsServices, TrademarkRecord

__all__ = [
    "CitationMetadata",
    "ConflictRanking",
    "GoodsServices",
    "MatchDisposition",
    "MatchResult",
    "TrademarkRecord",
    "compare_records",
    "normalize_jurisdiction",
    "normalize_nice_class",
]
