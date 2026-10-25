from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.evaluation.ocr_evaluation import DEFAULT_DATASET, evaluate_dataset
from app.services.analysis_service import AnalysisService
from app.services import ocr
from app.services.logo_match.exact_text import (
    exact_logo_text_match,
    normalize_logo_text,
)


class MyanmarEnglishOCRTests(unittest.TestCase):
    def test_myanmar_and_english_text_are_normalized_without_script_loss(self):
        burmese = "\u1019\u102d\u1014\u103a\u1038\u1002\u101c\u102c"
        self.assertEqual(len(normalize_logo_text(burmese)), len(burmese))
        self.assertEqual(normalize_logo_text("Shwe Myanmar\u2122"), "shwemyanmar")
        self.assertEqual(
            exact_logo_text_match("SAILUN", "Sailun\u2122")["text_match"],
            "EXACT",
        )

    def test_exact_comparison_does_not_invent_cross_script_transliteration(self):
        result = exact_logo_text_match(
            "\u101b\u103d\u103e\u1031\u1019\u103c\u1014\u103a\u1019\u102c",
            "Shwe Myanmar",
        )
        self.assertEqual(result["text_match"], "NOT_MATCH")

    def test_ocr_requests_both_english_and_myanmar_languages(self):
        with tempfile.NamedTemporaryFile(suffix=".png") as image:
            with patch.object(
                ocr.pytesseract,
                "image_to_string",
                return_value="\u1019\u103c\u1014\u103a\u1019\u102c Shwe",
            ) as recognize:
                text = ocr.extract_image_text(image.name)
        self.assertIn("Shwe", text)
        recognize.assert_called_once_with(image.name, lang="eng+mya")

    def test_missing_tesseract_is_reported_as_actionable_error(self):
        with tempfile.NamedTemporaryFile(suffix=".png") as image:
            with patch.object(
                ocr.pytesseract,
                "image_to_string",
                side_effect=ocr.TesseractNotFoundError(),
            ):
                with self.assertRaisesRegex(RuntimeError, "Tesseract OCR"):
                    ocr.extract_image_text(image.name)

    def test_ocr_text_is_used_in_visual_logo_comparison_when_mark_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            pdf_image = Path(directory) / "pdf.png"
            client_image = Path(directory) / "client.png"
            pdf_image.touch()
            client_image.touch()
            service = object.__new__(AnalysisService)
            with (
                patch.dict(os.environ, {"OCR_ENABLED": "true"}),
                patch(
                    "app.services.ocr.extract_image_text",
                    side_effect=[
                        "\u1019\u103c\u1014\u103a\u1019\u102c",
                        "\u1019\u103c\u1014\u103a\u1019\u102c",
                    ],
                ) as recognize,
                patch(
                    "app.services.similarity_engine.SimilarityEngine.compare",
                    return_value={"similarity_percent": 95, "status": "MATCH"},
                ),
            ):
                matches = service._compare_logos(
                    [{"image_path": str(pdf_image), "mark": ""}],
                    [{"image_path": str(client_image), "mark": ""}],
                )
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["text_match"], "EXACT")
        self.assertEqual(recognize.call_count, 2)

    def test_scanned_pdf_page_uses_page_ocr_and_preserves_trademark_crop(self):
        import pymupdf

        with tempfile.TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "scanned.pdf"
            pdf_document = pymupdf.open()
            pdf_document.new_page()
            pdf_document.save(pdf_path)
            pdf_document.close()
            service = object.__new__(AnalysisService)
            service.APPLICATION_RE = AnalysisService.APPLICATION_RE
            ocr_text = (
                "T/2024/123 (730): Owner (541): SAMPLE MARK (540)"
            )
            with (
                patch(
                    "app.services.ocr.extract_scanned_page_text",
                    return_value=(ocr_text, str(Path(directory) / "crop.png")),
                ),
                patch.object(service, "_extract_540_image", return_value=(None, None)),
            ):
                records = service._extract_pdf_records(
                    pdf_path=pdf_path,
                    output_dir=Path(directory),
                )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["application_no"], "T/2024/000123")
        self.assertEqual(records[0]["mark"], "SAMPLE MARK")
        self.assertEqual(records[0]["image_path"], str(Path(directory) / "crop.png"))


class LabeledOCREvaluationTests(unittest.TestCase):
    def test_synthetic_dataset_reports_false_positive_and_false_negative_counts(self):
        metrics = evaluate_dataset(DEFAULT_DATASET)
        self.assertEqual(metrics["ocr_text_only"]["samples"], 8)
        self.assertEqual(metrics["ocr_text_only"]["true_positive"], 3)
        self.assertEqual(metrics["ocr_text_only"]["false_positive"], 1)
        self.assertEqual(metrics["ocr_text_only"]["true_negative"], 3)
        self.assertEqual(metrics["ocr_text_only"]["false_negative"], 1)
        self.assertEqual(
            metrics["ocr_plus_curated_transliteration"]["true_positive"],
            4,
        )
        self.assertEqual(
            metrics["ocr_plus_curated_transliteration"]["false_positive"],
            1,
        )
        self.assertIn("not a representative", metrics["scope_note"])

    def test_invalid_labelled_dataset_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory) / "invalid.json"
            dataset.write_text(
                json.dumps([{"id": "invalid", "expected_conflict": "yes"}]),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "must contain"):
                evaluate_dataset(dataset)

    def test_real_image_dataset_runs_ocr_and_measures_character_error(self):
        from app.services.similarity_engine import SimilarityEngine

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "left.png").touch()
            (root / "right.png").touch()
            dataset = root / "real.json"
            dataset.write_text(
                json.dumps(
                    [
                        {
                            "id": "real-1",
                            "dataset_kind": "real",
                            "left_image": "left.png",
                            "right_image": "right.png",
                            "left_ground_truth_text": "SAILUN",
                            "right_ground_truth_text": "SAILUN",
                            "left_transliteration": "",
                            "right_transliteration": "",
                            "expected_conflict": True,
                            "adjudicator": "reviewer-1",
                            "adjudicated_at": "2026-09-28T12:00:00Z",
                            "source_reference": "registry-record-1",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            with (
                patch(
                    "app.evaluation.ocr_evaluation.extract_image_text",
                    side_effect=["SAILUN", "SAILUN"],
                ),
                patch.object(
                    SimilarityEngine,
                    "compare",
                    return_value={"similarity_percent": 95, "status": "MATCH"},
                ),
            ):
                report = evaluate_dataset(dataset, run_ocr=True)
        self.assertEqual(report["dataset_kind"], "real-image")
        self.assertEqual(report["ocr_character_error_rate"], 0.0)
        self.assertEqual(report["ocr_text_only"]["true_positive"], 1)


if __name__ == "__main__":
    unittest.main()
