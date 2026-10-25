"""Pure deterministic matching for jurisdiction and Nice-class-aware records."""

from dataclasses import dataclass
from enum import Enum
import re
import unicodedata

from .models import CitationMetadata, GoodsServices, TrademarkRecord


class MatchDisposition(str, Enum):
    CONFLICT = "conflict"
    NO_CONFLICT = "no_conflict"
    NEEDS_REVIEW = "needs_review"


class ConflictRanking(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"
    REVIEW = "review"


@dataclass(frozen=True)
class GoodsServicesOverlap:
    nice_class: int
    left_description: str
    right_description: str
    score: float


@dataclass(frozen=True)
class MatchResult:
    disposition: MatchDisposition
    ranking: ConflictRanking
    score: float
    normalized_jurisdiction: str | None
    shared_nice_classes: tuple[int, ...]
    overlaps: tuple[GoodsServicesOverlap, ...]
    review_reasons: tuple[str, ...]
    left_citation: CitationMetadata
    right_citation: CitationMetadata


_JURISDICTION_ALIASES = {
    "UNITED STATES": "US",
    "UNITED STATES OF AMERICA": "US",
    "USA": "US",
    "UK": "GB",
    "UNITED KINGDOM": "GB",
    "GREAT BRITAIN": "GB",
    "EUROPEAN UNION": "EU",
    "EUIPO": "EU",
    "WORLD INTELLECTUAL PROPERTY ORGANIZATION": "WO",
    "WIPO": "WO",
    "MADRID": "WO",
}
_STOP_WORDS = frozenset(
    {"a", "an", "and", "for", "in", "of", "or", "the", "to", "with"}
)


def normalize_jurisdiction(value: str) -> str:
    """Normalize a jurisdiction identifier without inferring legal equivalence."""
    if not isinstance(value, str):
        raise TypeError("jurisdiction must be a string")
    normalized = " ".join(value.strip().upper().replace("_", " ").split())
    if not normalized:
        raise ValueError("jurisdiction must not be empty")
    if normalized in _JURISDICTION_ALIASES:
        return _JURISDICTION_ALIASES[normalized]
    return re.sub(r"[\s.-]+", "", normalized)


def normalize_nice_class(value: int | str) -> int:
    """Return a validated Nice class number (1 through 45)."""
    if isinstance(value, bool):
        raise ValueError("Nice class must be an integer from 1 through 45")
    if isinstance(value, int):
        number = value
    elif isinstance(value, str):
        match = re.fullmatch(
            r"\s*(?:(?:nice\s*)?class\s*)?0*(\d{1,2})\s*",
            value,
            re.IGNORECASE,
        )
        if not match:
            raise ValueError(f"invalid Nice class: {value!r}")
        number = int(match.group(1))
    else:
        raise TypeError("Nice class must be an integer or string")
    if not 1 <= number <= 45:
        raise ValueError(f"Nice class must be from 1 through 45, got {number}")
    return number


def _tokens(text: str) -> frozenset[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return frozenset(
        token
        for token in re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)
        if token not in _STOP_WORDS
    )


def _text_similarity(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    union = left_tokens | right_tokens
    if not union:
        return 0.0
    return len(left_tokens & right_tokens) / len(union)


def _validated_goods_services(
    record: TrademarkRecord,
) -> tuple[tuple[int, str], ...]:
    normalized: list[tuple[int, str]] = []
    for item in record.goods_services:
        if not isinstance(item, GoodsServices):
            raise TypeError("goods_services entries must be GoodsServices instances")
        if not isinstance(item.description, str):
            raise TypeError("goods/services descriptions must be strings")
        normalized.append((normalize_nice_class(item.nice_class), item.description))
    return tuple(normalized)


def _ranking(score: float) -> ConflictRanking:
    if score >= 0.75:
        return ConflictRanking.HIGH
    if score >= 0.4:
        return ConflictRanking.MEDIUM
    if score > 0:
        return ConflictRanking.LOW
    return ConflictRanking.NONE


def compare_records(
    left: TrademarkRecord,
    right: TrademarkRecord,
    *,
    conflict_threshold: float = 0.35,
) -> MatchResult:
    """Compare records without network access; incomparable records need review.

    Only records with the same normalized jurisdiction and at least one shared
    Nice class are eligible for an automated conflict/no-conflict decision.
    """
    if not 0.0 <= conflict_threshold <= 1.0:
        raise ValueError("conflict_threshold must be between 0 and 1")

    left_jurisdiction = normalize_jurisdiction(left.jurisdiction)
    right_jurisdiction = normalize_jurisdiction(right.jurisdiction)
    left_items = _validated_goods_services(left)
    right_items = _validated_goods_services(right)
    left_classes = {nice_class for nice_class, _ in left_items}
    right_classes = {nice_class for nice_class, _ in right_items}
    shared_classes = tuple(sorted(left_classes & right_classes))

    review_reasons: list[str] = []
    if left_jurisdiction != right_jurisdiction:
        review_reasons.append("jurisdictions_are_not_comparable")
    if not left_classes or not right_classes:
        review_reasons.append("nice_class_data_missing")
    elif not shared_classes:
        review_reasons.append("no_shared_nice_classes")

    if review_reasons:
        return MatchResult(
            disposition=MatchDisposition.NEEDS_REVIEW,
            ranking=ConflictRanking.REVIEW,
            score=0.0,
            normalized_jurisdiction=(
                left_jurisdiction if left_jurisdiction == right_jurisdiction else None
            ),
            shared_nice_classes=shared_classes,
            overlaps=(),
            review_reasons=tuple(review_reasons),
            left_citation=left.citation,
            right_citation=right.citation,
        )

    overlaps = tuple(
        GoodsServicesOverlap(
            nice_class=nice_class,
            left_description=left_description,
            right_description=right_description,
            score=_text_similarity(left_description, right_description),
        )
        for nice_class in shared_classes
        for left_class, left_description in left_items
        if left_class == nice_class
        for right_class, right_description in right_items
        if right_class == nice_class
    )
    score = max((overlap.score for overlap in overlaps), default=0.0)
    disposition = (
        MatchDisposition.CONFLICT
        if score >= conflict_threshold
        else MatchDisposition.NO_CONFLICT
    )
    return MatchResult(
        disposition=disposition,
        ranking=_ranking(score),
        score=score,
        normalized_jurisdiction=left_jurisdiction,
        shared_nice_classes=shared_classes,
        overlaps=overlaps,
        review_reasons=(),
        left_citation=left.citation,
        right_citation=right.citation,
    )
