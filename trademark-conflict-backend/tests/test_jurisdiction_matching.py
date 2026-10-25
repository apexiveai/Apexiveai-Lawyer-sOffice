import unittest
from datetime import datetime, timezone

from app.services.jurisdiction import (
    CitationMetadata,
    ConflictRanking,
    GoodsServices,
    MatchDisposition,
    TrademarkRecord,
    compare_records,
    normalize_jurisdiction,
    normalize_nice_class,
)


class JurisdictionNormalizationTests(unittest.TestCase):
    def test_normalizes_common_jurisdiction_aliases(self):
        self.assertEqual(normalize_jurisdiction(" united states "), "US")
        self.assertEqual(normalize_jurisdiction("USA"), "US")
        self.assertEqual(normalize_jurisdiction("United_Kingdom"), "GB")
        self.assertEqual(normalize_jurisdiction(" eu "), "EU")
        self.assertEqual(normalize_jurisdiction("ca"), "CA")
        self.assertEqual(normalize_jurisdiction("us-pto"), "USPTO")

    def test_rejects_empty_or_non_string_jurisdictions(self):
        with self.assertRaises(ValueError):
            normalize_jurisdiction("  ")
        with self.assertRaises(TypeError):
            normalize_jurisdiction(None)  # type: ignore[arg-type]

    def test_normalizes_numeric_and_labeled_nice_classes(self):
        self.assertEqual(normalize_nice_class(9), 9)
        self.assertEqual(normalize_nice_class("09"), 9)
        self.assertEqual(normalize_nice_class("Class 9"), 9)
        self.assertEqual(normalize_nice_class("Nice Class 09"), 9)
        self.assertEqual(normalize_nice_class(" class 045 "), 45)

    def test_rejects_invalid_nice_classes(self):
        for value in (0, 46, "Class 0", "Class 46", "nine", True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_nice_class(value)
        with self.assertRaises(TypeError):
            normalize_nice_class(None)  # type: ignore[arg-type]


class JurisdictionMatchingTests(unittest.TestCase):
    def setUp(self):
        self.citation_a = CitationMetadata(
            source_name="Example National Registry",
            source_url="https://registry.example/records/123",
            retrieved_at=datetime(2026, 9, 28, tzinfo=timezone.utc),
            source_record_id="123",
        )
        self.citation_b = CitationMetadata(
            source_name="Example National Registry",
            source_url="https://registry.example/records/456",
            retrieved_at=datetime(2026, 9, 28, tzinfo=timezone.utc),
            source_record_id="456",
        )

    def record(self, jurisdiction, items, citation):
        return TrademarkRecord(
            jurisdiction=jurisdiction,
            goods_services=tuple(items),
            citation=citation,
        )

    def test_identical_goods_services_in_same_jurisdiction_and_class_conflict(self):
        result = compare_records(
            self.record("US", [GoodsServices(9, "downloadable computer software")], self.citation_a),
            self.record("usa", [GoodsServices("Class 09", "downloadable computer software")], self.citation_b),
        )

        self.assertEqual(result.disposition, MatchDisposition.CONFLICT)
        self.assertEqual(result.ranking, ConflictRanking.HIGH)
        self.assertEqual(result.score, 1.0)
        self.assertEqual(result.normalized_jurisdiction, "US")
        self.assertEqual(result.shared_nice_classes, (9,))
        self.assertEqual(result.left_citation, self.citation_a)
        self.assertEqual(result.right_citation, self.citation_b)
        self.assertEqual(result.overlaps[0].score, 1.0)

    def test_text_similarity_is_case_and_word_order_independent(self):
        left = self.record("US", [GoodsServices(9, "Software for computers")], self.citation_a)
        right = self.record("US", [GoodsServices(9, "COMPUTERS software")], self.citation_b)

        result = compare_records(left, right)

        self.assertEqual(result.score, 1.0)
        self.assertEqual(result.disposition, MatchDisposition.CONFLICT)

    def test_partial_overlap_produces_deterministic_jaccard_score(self):
        left = self.record("US", [GoodsServices(9, "computer software")], self.citation_a)
        right = self.record("US", [GoodsServices(9, "computer hardware")], self.citation_b)

        result = compare_records(left, right)

        self.assertAlmostEqual(result.score, 1 / 3)
        self.assertEqual(result.ranking, ConflictRanking.LOW)
        self.assertEqual(result.disposition, MatchDisposition.NO_CONFLICT)

    def test_similar_descriptions_in_different_jurisdictions_need_review(self):
        left = self.record("US", [GoodsServices(9, "computer software")], self.citation_a)
        right = self.record("CA", [GoodsServices(9, "computer software")], self.citation_b)

        result = compare_records(left, right)

        self.assertEqual(result.disposition, MatchDisposition.NEEDS_REVIEW)
        self.assertEqual(result.ranking, ConflictRanking.REVIEW)
        self.assertIsNone(result.normalized_jurisdiction)
        self.assertEqual(result.review_reasons, ("jurisdictions_are_not_comparable",))
        self.assertEqual(result.score, 0.0)
        self.assertEqual(result.left_citation, self.citation_a)

    def test_records_with_no_shared_nice_class_need_review(self):
        left = self.record("US", [GoodsServices(9, "computer software")], self.citation_a)
        right = self.record("US", [GoodsServices(42, "software design")], self.citation_b)

        result = compare_records(left, right)

        self.assertEqual(result.disposition, MatchDisposition.NEEDS_REVIEW)
        self.assertEqual(result.review_reasons, ("no_shared_nice_classes",))
        self.assertEqual(result.shared_nice_classes, ())
        self.assertEqual(result.overlaps, ())

    def test_missing_class_data_needs_review(self):
        left = self.record("US", [], self.citation_a)
        right = self.record("US", [GoodsServices(9, "computer software")], self.citation_b)

        result = compare_records(left, right)

        self.assertEqual(result.disposition, MatchDisposition.NEEDS_REVIEW)
        self.assertEqual(result.review_reasons, ("nice_class_data_missing",))

    def test_different_classes_and_jurisdictions_report_each_review_reason(self):
        left = self.record("US", [GoodsServices(9, "computer software")], self.citation_a)
        right = self.record("CA", [GoodsServices(42, "software design")], self.citation_b)

        result = compare_records(left, right)

        self.assertEqual(
            result.review_reasons,
            ("jurisdictions_are_not_comparable", "no_shared_nice_classes"),
        )

    def test_multiple_class_pairs_choose_the_highest_overlap(self):
        left = self.record(
            "US",
            [GoodsServices(9, "computer software"), GoodsServices(42, "design services")],
            self.citation_a,
        )
        right = self.record(
            "US",
            [GoodsServices(9, "computer hardware"), GoodsServices(42, "design services")],
            self.citation_b,
        )

        result = compare_records(left, right)

        self.assertEqual(result.shared_nice_classes, (9, 42))
        self.assertEqual(len(result.overlaps), 2)
        self.assertEqual(result.score, 1.0)
        self.assertEqual(result.disposition, MatchDisposition.CONFLICT)
        self.assertEqual(result.overlaps[1].nice_class, 42)

    def test_custom_threshold_changes_only_the_disposition(self):
        left = self.record("US", [GoodsServices(9, "computer software")], self.citation_a)
        right = self.record("US", [GoodsServices(9, "computer hardware")], self.citation_b)

        default = compare_records(left, right)
        lowered = compare_records(left, right, conflict_threshold=0.3)

        self.assertEqual(default.score, lowered.score)
        self.assertEqual(default.ranking, lowered.ranking)
        self.assertEqual(default.disposition, MatchDisposition.NO_CONFLICT)
        self.assertEqual(lowered.disposition, MatchDisposition.CONFLICT)

    def test_empty_text_has_zero_score_without_false_conflict(self):
        left = self.record("US", [GoodsServices(9, "and the")], self.citation_a)
        right = self.record("US", [GoodsServices(9, "")], self.citation_b)

        result = compare_records(left, right)

        self.assertEqual(result.score, 0.0)
        self.assertEqual(result.ranking, ConflictRanking.NONE)
        self.assertEqual(result.disposition, MatchDisposition.NO_CONFLICT)

    def test_rejects_invalid_threshold_and_class_data(self):
        left = self.record("US", [GoodsServices(0, "test")], self.citation_a)
        right = self.record("US", [GoodsServices(9, "test")], self.citation_b)
        with self.assertRaises(ValueError):
            compare_records(left, right)

        valid = self.record("US", [GoodsServices(9, "test")], self.citation_a)
        with self.assertRaises(ValueError):
            compare_records(valid, valid, conflict_threshold=1.1)


if __name__ == "__main__":
    unittest.main()
