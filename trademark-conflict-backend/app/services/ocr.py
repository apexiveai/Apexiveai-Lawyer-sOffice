from __future__ import annotations

import os
from pathlib import Path
import re
import tempfile

import cv2
import pymupdf
import pytesseract
from pytesseract import Output, TesseractError, TesseractNotFoundError


def ocr_is_enabled() -> bool:
    return os.getenv("OCR_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def extract_image_text(
    image_path: str | Path,
    languages: str | None = None,
) -> str:
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"OCR image does not exist: {path}")

    language_config = languages or os.getenv("OCR_LANGUAGES", "eng+mya")
    if not language_config.strip():
        raise ValueError("OCR_LANGUAGES must name at least one Tesseract language.")

    try:
        return pytesseract.image_to_string(
            str(path),
            lang=language_config,
        ).strip()
    except TesseractNotFoundError as error:
        raise RuntimeError(
            "Tesseract OCR is not installed or not available on PATH."
        ) from error
    except TesseractError as error:
        raise RuntimeError(
            "Tesseract OCR failed. Verify the configured language data exists "
            f"for {language_config!r}."
        ) from error


def extract_scanned_page_text(
    page: pymupdf.Page,
    output_dir: str | Path,
    page_number: int,
    languages: str | None = None,
) -> tuple[str, str | None]:
    if not ocr_is_enabled():
        return "", None

    output_directory = Path(output_dir)
    output_directory.mkdir(parents=True, exist_ok=True)
    language_config = languages or os.getenv("OCR_LANGUAGES", "eng+mya")

    try:
        with tempfile.TemporaryDirectory(prefix="trademark-ocr-") as temporary_dir:
            page_image = Path(temporary_dir) / "page.png"
            page.get_pixmap(matrix=pymupdf.Matrix(3, 3), alpha=False).save(
                str(page_image)
            )
            data = pytesseract.image_to_data(
                str(page_image),
                lang=language_config,
                output_type=Output.DICT,
            )
            tokens = [
                (index, value.strip())
                for index, value in enumerate(data.get("text", []))
                if value and value.strip()
            ]
            text = " ".join(value for _, value in tokens)
            tag_indices = [
                index
                for index, value in tokens
                if re.sub(r"\D", "", value) == "540"
            ]
            if not tag_indices:
                return text, None

            tag_index = tag_indices[0]
            bottom = int(data["top"][tag_index]) + int(data["height"][tag_index])
            image = cv2.imread(str(page_image), cv2.IMREAD_COLOR)
            if image is None:
                raise RuntimeError("Could not read the rendered scanned PDF page.")
            crop_top = min(bottom + 15, image.shape[0] - 1)
            crop_bottom = min(
                crop_top + round(250 * 3),
                image.shape[0],
            )
            if crop_bottom <= crop_top:
                return text, None
            crop_path = output_directory / f"page_{page_number:04d}_trademark.png"
            if not cv2.imwrite(
                str(crop_path),
                image[crop_top:crop_bottom, :],
            ):
                raise RuntimeError(
                    f"Could not save scanned trademark crop: {crop_path}"
                )
            return text, str(crop_path)
    except TesseractNotFoundError as error:
        raise RuntimeError(
            "Tesseract OCR is not installed or not available on PATH."
        ) from error
    except TesseractError as error:
        raise RuntimeError(
            "Tesseract OCR failed. Verify the configured language data exists "
            f"for {language_config!r}."
        ) from error
