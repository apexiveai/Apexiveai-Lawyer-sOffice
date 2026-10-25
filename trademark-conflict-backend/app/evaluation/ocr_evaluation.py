from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from app.services.ocr import extract_image_text
from app.services.logo_match.decision import decide_logo_match
from app.services.logo_match.exact_text import exact_logo_text_match

DEFAULT_DATASET = (
    Path(__file__).resolve().parents[2]
    / "evaluation"
    / "labelled_ocr_pairs.json"
)


def _confusion_matrix(rows: list[dict[str, Any]], *, use_transliteration: bool) -> dict:
    true_positive = false_positive = true_negative = false_negative = 0
    for row in rows:
        if "visual_similarity" in row:
            predicted = decide_logo_match(
                row["left_ocr_text"],
                row["right_ocr_text"],
                row["visual_similarity"],
            )["logo_match"]
            if row.get("visual_status") == "EXACT":
                predicted = True
        else:
            predicted = exact_logo_text_match(
                row["left_ocr_text"],
                row["right_ocr_text"],
            )["text_match"] == "EXACT"
        if use_transliteration:
            left_transliteration = row.get("left_transliteration", "")
            right_transliteration = row.get("right_transliteration", "")
            if left_transliteration and right_transliteration:
                if "visual_similarity" in row:
                    predicted = decide_logo_match(
                        left_transliteration,
                        right_transliteration,
                        row["visual_similarity"],
                    )["logo_match"]
                    if row.get("visual_status") == "EXACT":
                        predicted = True
                else:
                    predicted = (
                        exact_logo_text_match(
                            left_transliteration,
                            right_transliteration,
                        )["text_match"]
                        == "EXACT"
                    )

        actual = row["expected_conflict"]
        if predicted and actual:
            true_positive += 1
        elif predicted:
            false_positive += 1
        elif actual:
            false_negative += 1
        else:
            true_negative += 1

    total = len(rows)
    precision_denominator = true_positive + false_positive
    recall_denominator = true_positive + false_negative
    precision = (
        true_positive / precision_denominator if precision_denominator else 0.0
    )
    recall = true_positive / recall_denominator if recall_denominator else 0.0
    return {
        "samples": total,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "true_negative": true_negative,
        "false_negative": false_negative,
        "accuracy": (
            (true_positive + true_negative) / total if total else 0.0
        ),
        "precision": precision,
        "recall": recall,
        "f1": (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        ),
    }


def _character_error_counts(actual: str, expected: str) -> tuple[int, int]:
    previous = list(range(len(expected) + 1))
    for actual_index, actual_character in enumerate(actual, start=1):
        current = [actual_index]
        for expected_index, expected_character in enumerate(expected, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[expected_index] + 1,
                    previous[expected_index - 1]
                    + (actual_character != expected_character),
                )
            )
        previous = current
    return previous[-1], len(expected)


def evaluate_dataset(
    dataset_path: str | Path = DEFAULT_DATASET,
    *,
    run_ocr: bool = False,
) -> dict:
    path = Path(dataset_path)
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read labeled OCR dataset: {path}") from error
    if not isinstance(rows, list) or not rows:
        raise ValueError("The labeled OCR dataset must be a non-empty JSON array.")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("Every labeled OCR sample must be a JSON object.")
    real_dataset = any(row.get("dataset_kind") == "real" for row in rows)
    if real_dataset and not all(row.get("dataset_kind") == "real" for row in rows):
        raise ValueError("Do not mix real and synthetic OCR samples in one dataset.")
    required = (
        {
            "id",
            "dataset_kind",
            "left_image",
            "right_image",
            "left_ground_truth_text",
            "right_ground_truth_text",
            "expected_conflict",
            "adjudicator",
            "adjudicated_at",
            "source_reference",
        }
        if real_dataset
        else {"id", "left_ocr_text", "right_ocr_text", "expected_conflict"}
    )
    prepared_rows = []
    total_character_errors = 0
    total_reference_characters = 0
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not required.issubset(row):
            raise ValueError(
                f"Dataset row {index + 1} must contain {sorted(required)}."
            )
        if not isinstance(row["expected_conflict"], bool):
            raise ValueError(
                f"Dataset row {index + 1} expected_conflict must be boolean."
            )
        if real_dataset:
            if not row["adjudicator"].strip() or not row["source_reference"].strip():
                raise ValueError(
                    f"Real dataset row {index + 1} requires adjudicator and source reference."
                )
            try:
                datetime.fromisoformat(row["adjudicated_at"].replace("Z", "+00:00"))
            except (AttributeError, ValueError) as error:
                raise ValueError(
                    f"Real dataset row {index + 1} adjudicated_at must be ISO 8601."
                ) from error
            left_image = (path.parent / row["left_image"]).resolve()
            right_image = (path.parent / row["right_image"]).resolve()
            if not left_image.is_file() or not right_image.is_file():
                raise ValueError(
                    f"Real dataset row {index + 1} is missing one or both image files."
                )
            left_text = extract_image_text(left_image) if run_ocr else ""
            right_text = extract_image_text(right_image) if run_ocr else ""
            if run_ocr:
                for actual, expected in (
                    (left_text, row["left_ground_truth_text"]),
                    (right_text, row["right_ground_truth_text"]),
                ):
                    errors, reference_characters = _character_error_counts(
                        actual,
                        expected,
                    )
                    total_character_errors += errors
                    total_reference_characters += reference_characters
            prepared_rows.append(
                {
                    **row,
                    "left_ocr_text": left_text,
                    "right_ocr_text": right_text,
                }
            )
            from app.services.similarity_engine import SimilarityEngine

            visual_result = SimilarityEngine(threshold=0.0).compare(
                str(left_image),
                str(right_image),
            )
            prepared_rows[-1]["visual_similarity"] = float(
                visual_result.get("similarity_percent", 0.0)
            ) / 100.0
            prepared_rows[-1]["visual_status"] = visual_result.get("status")
        else:
            prepared_rows.append(row)
    if real_dataset and not run_ocr:
        raise ValueError(
            "Real image datasets require --run-ocr to measure recognition output."
        )
    return {
        "dataset": path.name,
        "dataset_kind": "real-image" if real_dataset else "synthetic-text",
        "scope_note": (
            "Metrics are meaningful only for independently adjudicated and "
            "representative input. Text-only fixtures are not production accuracy."
        ),
        "ocr_text_only": _confusion_matrix(
            prepared_rows,
            use_transliteration=False,
        ),
        "ocr_plus_curated_transliteration": _confusion_matrix(
            prepared_rows,
            use_transliteration=True,
        ),
        "ocr_character_error_rate": (
            total_character_errors / total_reference_characters
            if real_dataset and total_reference_characters
            else None
        ),
        "ocr_reference_characters": (
            total_reference_characters if real_dataset else None
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help="Path to a JSON array of labeled OCR text pairs.",
    )
    parser.add_argument(
        "--run-ocr",
        action="store_true",
        help="Run Tesseract on labeled images and report character error rate.",
    )
    arguments = parser.parse_args()
    print(
        json.dumps(
            evaluate_dataset(arguments.dataset, run_ocr=arguments.run_ocr),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
