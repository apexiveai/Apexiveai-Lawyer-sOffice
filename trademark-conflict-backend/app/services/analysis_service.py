
from __future__ import annotations

import json

import re
import sys

from pathlib import Path

from typing import Any, Callable, Dict, List, Optional, Tuple

import cv2

import numpy as np

import pymupdf as pymupdf

from openpyxl import load_workbook
from app.services.ai_logo.verifier import LogoAIVerifier
from app.core.config import EVIDENCE_DIR, EXTRACTED_DIR

from app.services.pdf_extractor import PDFExtractor

from app.services.xlsx_extractor import XLSXExtractor

from app.services.similarity_engine import SimilarityEngine

class AnalysisService:

    """

    Production trademark conflict analysis.

    Pipeline:

        1. Read PDF / XLSX

        2. Extract client records + logos

        3. Detect PDF trademark records

        4. Extract exact (540) trademark images

        5. Compare PDF logos with XLSX logos

        6. Match application numbers

        7. Match company names

        8. Match phone numbers

        9. Render visual evidence

       10. Return frontend-ready JSON

    """

    APPLICATION_RE = re.compile(

        r"(?:MM\s*/\s*)?T\s*/\s*((?:19|20)\d{2})\s*/\s*(\d{1,8})",

        re.IGNORECASE,

    )

    PHONE_RE = re.compile(

        r"(?:\+?95|09)[\s\-().]*\d[\d\s\-().]{5,}",

        re.IGNORECASE,

    )

    def __init__(

        self,

        pdf_path: str,

        xlsx_path: Optional[str] = None,

        job_id: str = "",

        client_pdf_path: Optional[str] = None,
        left_xlsx_path: Optional[str] = None,
        right_xlsx_path: Optional[str] = None,
        progress_callback: Callable[[int, str], None] | None = None,
        analysis_metadata: Dict[str, Any] | None = None,

    ):

        self.pdf_path = Path(pdf_path)

        self.xlsx_path = Path(xlsx_path) if xlsx_path else None
        self.client_pdf_path = Path(client_pdf_path) if client_pdf_path else None
        self.left_xlsx_path = Path(left_xlsx_path) if left_xlsx_path else None
        self.right_xlsx_path = Path(right_xlsx_path) if right_xlsx_path else None
        self._client_pdf_records: List[Dict[str, Any]] = []
        self.progress_callback = progress_callback
        self.analysis_metadata = analysis_metadata or {}

        self.job_id = job_id

        self.job_extracted_dir = EXTRACTED_DIR / job_id

        self.job_pdf_dir = self.job_extracted_dir / "pdf_trademarks"

        self.job_client_dir = self.job_extracted_dir / "xlsx"

        self.evidence_dir = EVIDENCE_DIR / job_id

        self.evidence_dir.mkdir(parents=True, exist_ok=True)

        self.job_pdf_dir.mkdir(parents=True, exist_ok=True)

        self.similarity_engine = SimilarityEngine(

            threshold=0.82

        )
        self.ai_verifier = LogoAIVerifier(
            high_threshold=0.90,
            review_threshold=0.82,
        )

    # ============================================================

    # PUBLIC

    # ============================================================

    def run(self) -> Dict[str, Any]:

        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(
                encoding="utf-8",
                errors="backslashreplace",
            )

        if self.left_xlsx_path and self.right_xlsx_path:
            return self._run_xlsx_pair()

        self._report_progress(5, "Loading source documents.")

        print()

        print("=" * 60)

        print("TRADEMARK CONFLICT ANALYSIS")

        print("=" * 60)

        # --------------------------------------------------------

        # 1. PDF

        # --------------------------------------------------------

        print("[1/8] Loading PDF...")

        pdf_extractor = PDFExtractor(

            pdf_path=str(self.pdf_path)

        )

        pdf_pages = pdf_extractor.get_page_count()
        self._report_progress(15, "Government PDF loaded.")

        print(f"      PDF pages: {pdf_pages}")

        if self.client_pdf_path:
            print("[2/8] Loading client PDF...")
            client_rows = self._extract_pdf_records(
                pdf_path=self.client_pdf_path,
                output_dir=self.job_extracted_dir / "client_pdf",
                source_type="client_pdf",
            )
            client_records = len(client_rows)
            for row_number, client_logo in enumerate(client_rows, start=1):
                client_logo["row"] = row_number
                client_logo["sheet"] = self.client_pdf_path.stem
                client_logo["client_owner"] = client_logo.get("owner")
                client_logo["client"] = client_logo.get("owner")
                client_logo["mark"] = client_logo.get("mark")
                client_logo["application_no"] = client_logo.get("application_no")
            self._client_pdf_records = client_rows
            client_logos = [
                record for record in client_rows
                if record.get("image_path")
            ]
        else:
            print("[2/8] Loading client XLSX...")
            xlsx_extractor = XLSXExtractor(xlsx_path=str(self.xlsx_path))
            client_rows = self._get_client_rows()
            client_records = len(client_rows)
            client_logos = xlsx_extractor.extract_images(self.job_id)
        self._report_progress(30, "Client records and logos extracted.")

        client_row_map = {}

        for client_row in client_rows:

            sheet_name = str(

                client_row.get("sheet") or ""

            ).strip()

            row_number = client_row.get("row")

            if not sheet_name or row_number is None:

                continue

            key = (

                sheet_name,

                int(row_number),

            )

            client_row_map[key] = client_row

        for client_logo in client_logos:
            if self.client_pdf_path:
                continue

            sheet_name = str(

            client_logo.get("sheet") or ""

            ).strip()

            row_number = client_logo.get("row")

            if not sheet_name or row_number is None:

                continue

            key = (

                sheet_name,

                int(row_number),

            )

            client_row = client_row_map.get(key)

            if not client_row:

                continue

    # Preserve image/extraction metadata.

            client_logo["sheet"] = client_row.get(

                "sheet",

                client_logo.get("sheet"),

            )

            client_logo["row"] = client_row.get(

                "row",

                client_logo.get("row"),

            )

            client_logo["owner"] = client_row.get(

                "owner"

            )

            client_logo["client_owner"] = client_row.get(

                "owner"

            )

            client_logo["application_no"] = client_row.get(

                "application_no"

            )

            client_logo["client"] = client_row.get(

                "client"

            )

            client_logo["mark"] = client_row.get(

                "mark"

            )

            client_logo["phone"] = client_row.get(

                "phone"

            )

    # Keep the complete source row for evidence/debugging.

            client_logo["row_data"] = client_row

        print(

            f"      Client records: "

            f"{client_records}"

        )

        print(

            f"      Client logos: "

            f"{len(client_logos)}"

        )

# Diagnostic metadata check.

        for index, logo in enumerate(

            client_logos[:10],

            start=1,

        ):

            print(

                f"      XLSX LOGO {index}: "

                f"sheet={logo.get('sheet')} "

                f"row={logo.get('row')} "

                f"owner={logo.get('client_owner')} "

                f"application={logo.get('application_no')} "

                f"mark={logo.get('mark')}"

            )

        print("[3/8] Detecting PDF trademark records...")

        pdf_records = self._extract_pdf_records()
        self._report_progress(45, "Trademark records extracted.")

        print(

            f"      PDF trademark records: "

            f"{len(pdf_records)}"

        )

        pdf_logos = [

            record

            for record in pdf_records

            if record.get("image_path")

        ]

        print(

            f"      PDF trademark logos: "

            f"{len(pdf_logos)}"

        )

        # --------------------------------------------------------

        # 4. Application / company / phone matching

        # --------------------------------------------------------

        print("[4/8] Matching text data...")

        application_matches = self._match_application_records(

            pdf_records

        )

        company_matches = self._match_company_records(

            pdf_records,
            client_logos

        )

        phone_matches = self._match_phone_records(
            pdf_records
        )
        self._report_progress(60, "Text-based conflict checks completed.")

        print(

            f"      Application matches: "

            f"{len(application_matches)}"

        )

        print(

            f"      Company matches: "

            f"{len(company_matches)}"

        )

        print(

            f"      Phone matches: "

            f"{len(phone_matches)}"

        )

        # --------------------------------------------------------

        # 5. Logo comparison

        # --------------------------------------------------------

        print("[5/8] Comparing trademark logos...")

        logo_matches = self._compare_logos(
            pdf_logos=pdf_logos,
            client_logos=client_logos,
        )
        self._report_progress(80, "Logo comparison completed.")
        print(
            f"      Logo matches: "
            f"{len(logo_matches)}"

        )

        # --------------------------------------------------------

        # 6. Combine

        # --------------------------------------------------------

        print("[6/8] Combining conflict results...")

        matches = self._combine_matches(

            application_matches=application_matches,

            company_matches=company_matches,

            phone_matches=phone_matches,

            logo_matches=logo_matches,

        )

        # --------------------------------------------------------

        # 7. Evidence

        # --------------------------------------------------------

        print("[7/8] Rendering evidence...")

        for index, match in enumerate(matches, start=1):

            try:

                self._render_match_evidence(

                    match,

                    index,

                )

            except Exception as error:

                import traceback

                print(

                    f"      Evidence warning: "

                    f"{type(error).__name__}: {error}"

                )

                traceback.print_exc()
            if index % 10 == 0 or index == len(matches):
                self._report_progress(
                    min(95, 80 + int(15 * index / max(len(matches), 1))),
                    f"Rendered evidence for {index} of {len(matches)} matches.",
                )

        print("[8/8] Analysis complete.")

        result = {

            "job_id": self.job_id,

            "left_file_type": "pdf",
            "right_file_type": (
                "pdf" if self.client_pdf_path else "xlsx"
            ),

            "pdf_pages": pdf_pages,

            "client_records": client_records,

            "pdf_logos": len(pdf_logos),

            "xlsx_logos": len(client_logos),

            "application_matches": len(

                application_matches

            ),

            "logo_matches": len(

                logo_matches

            ),

            "company_matches": len(

                company_matches

            ),

            "phone_matches": len(

                phone_matches

            ),

            "matches": matches,
            **self.analysis_metadata,

            "application_match_details":

                application_matches,

            "company_match_details":

                company_matches,

            "phone_match_details":

                phone_matches,

            "logo_match_details":

                logo_matches,

        }

        print()

        print("=" * 60)

        print(

            f"PDF PAGES          : "

            f"{result['pdf_pages']}"

        )

        print(

            f"CLIENT RECORDS     : "

            f"{result['client_records']}"

        )

        print(

            f"PDF LOGOS          : "

            f"{result['pdf_logos']}"

        )

        print(

            f"XLSX LOGOS         : "

            f"{result['xlsx_logos']}"

        )

        print(

            f"APPLICATION MATCHES: "

            f"{result['application_matches']}"

        )

        print(

            f"LOGO MATCH         : "

            f"{result['logo_matches']}"

        )

        print(

            f"COMPANY MATCH      : "

            f"{result['company_matches']}"

        )

        print(

            f"PHONE MATCH        : "

            f"{result['phone_matches']}"

        )

        print("=" * 60)



        # --------------------------------------------------------

        # Persist complete analysis result

        # --------------------------------------------------------

        try:

            result_path = (

                self.evidence_dir /

                "analysis_result.json"

            )

            result_path.write_text(

                json.dumps(

                    result,

                    ensure_ascii=False,

                    indent=2,

                    default=str,

                ),

                encoding="utf-8",

            )

            print(

                f"      Result saved: "

                f"{result_path}"

            )

        except Exception as error:

            print(

                "      Result persistence warning: "

                f"{type(error).__name__}: {error}"

            )

        return result

    def _run_xlsx_pair(self) -> Dict[str, Any]:
        self._report_progress(10, "Extracting trademark images from workbooks.")
        left = XLSXExtractor(str(self.left_xlsx_path)).extract_images(
            f"{self.job_id}_left"
        )
        right = XLSXExtractor(str(self.right_xlsx_path)).extract_images(
            f"{self.job_id}_right"
        )
        left = [item for item in left if item.get("image_path")]
        right = [item for item in right if item.get("image_path")]
        self._report_progress(40, "Comparing workbook trademark images.")
        for item in left:
            item["source_type"] = "xlsx_left"
        for item in right:
            item["source_type"] = "xlsx_right"
        logo_matches = self._compare_logos(left, right)
        self._report_progress(80, "Workbook logo comparison completed.")
        matches = self._combine_matches([], [], [], logo_matches)
        for index, match in enumerate(matches, start=1):
            self._render_match_evidence(match, index)
        result = {
            "job_id": self.job_id,
            "left_file_type": "xlsx",
            "right_file_type": "xlsx",
            "pdf_pages": 0,
            "client_records": len(right),
            "pdf_logos": len(left),
            "xlsx_logos": len(right),
            "application_matches": 0,
            "logo_matches": len(logo_matches),
            "company_matches": 0,
            "phone_matches": 0,
            "matches": matches,
            **self.analysis_metadata,
            "application_match_details": [],
            "company_match_details": [],
            "phone_match_details": [],
            "logo_match_details": logo_matches,
        }
        self._persist_result(result)
        self._report_progress(100, "Analysis results saved.")
        return result

    def _report_progress(self, progress: int, message: str) -> None:
        if self.progress_callback is not None:
            self.progress_callback(progress, message)

    def _persist_result(self, result: Dict[str, Any]) -> None:
        result_path = self.evidence_dir / "analysis_result.json"
        result_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def _get_client_record_count(self) -> int:

        workbook = load_workbook(

            self.xlsx_path,

            read_only=True,

            data_only=True,

        )

        count = 0

        try:

            for worksheet in workbook.worksheets:

                for row in worksheet.iter_rows(

                    values_only=True

                ):

                    values = [

                        value

                        for value in row

                        if value is not None

                        and str(value).strip()

                    ]

                    if not values:

                        continue

                    first = str(values[0]).strip()

                    # Skip header rows.

                    if first.lower() in {

                        "no.",

                        "no",

                        "number",

                    }:

                        continue

                    # A record normally has a numeric No.

                    if isinstance(values[0], int):

                        count += 1

        finally:

            workbook.close()

        return count

    def _extract_pdf_records(
        self,
        pdf_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        source_type: str = "pdf",
    ) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        source_path = pdf_path or self.pdf_path
        destination_dir = output_dir or self.job_pdf_dir
        destination_dir.mkdir(parents=True, exist_ok=True)

        with pymupdf.open(source_path) as document:

            for page_index, page in enumerate(

                document,

                start=1,

            ):

                text = page.get_text("text")
                scanned_image_path = None
                if not text.strip():
                    from app.services.ocr import extract_scanned_page_text

                    text, scanned_image_path = extract_scanned_page_text(
                        page,
                        destination_dir,
                        page_index,
                    )
                if not text.strip():
                    continue

                application_match = (

                    self.APPLICATION_RE.search(text)

                )

                if not application_match:

                    continue

                application_no = self._normalize_application(

                    application_match

                )

                owner = self._extract_owner(

                    text

                )

                phone = self._extract_phone(

                    text

                )

                mark = self._extract_mark(

                    text

                )

                image_path, image_bbox = (

                    self._extract_540_image(
                        document=document,
                        page=page,
                        page_number=page_index,
                        output_dir=destination_dir,
                    )

                )
                if image_path is None and scanned_image_path is not None:
                    image_path = scanned_image_path
                if not mark and image_path:
                    from app.services.ocr import extract_image_text, ocr_is_enabled

                    if ocr_is_enabled():
                        mark = extract_image_text(image_path)

                record = {

                    "id": (

                        f"pdf_trademark_"

                        f"{page_index}"

                    ),

                    "source_type": source_type,
                    "source_file":
                        source_path.name,

                    "page": page_index,

                    "application_no":

                        application_no,

                    "owner":

                        owner,

                    "phone":

                        phone,

                    "mark":

                        mark,

                    "image_path":

                        image_path,

                    "bbox":

                        image_bbox,

                    "confidence": 1.0,

                }

                records.append(record)

        return records

    # ============================================================

    # PDF 540 IMAGE

    # ============================================================

    def _extract_540_image(

        self,

        document,

        page,

        page_number: int,
        output_dir: Optional[Path] = None,

    ) -> Tuple[Optional[str], Optional[List[float]]]:

        text_blocks = page.get_text(

            "dict"

        ).get("blocks", [])

        target_y = None

        for block in text_blocks:

            if block.get("type") != 0:

                continue

            block_text = "".join(

                span.get("text", "")

                for line in block.get("lines", [])

                for span in line.get("spans", [])

            ).strip()

            if block_text.startswith("(540)"):

                bbox = block.get("bbox")

                if bbox:

                    target_y = bbox[1]

                break

        if target_y is None:

            return None, None

        image_candidates = []

        for image_info in page.get_images(

            full=True

        ):

            xref = image_info[0]

            try:

                rects = page.get_image_rects(

                    xref

                )

            except Exception:

                continue

            for rect in rects:

                # Image must start at / below (540)

                # and reasonably close to the label.

                if rect.y0 >= target_y - 5:

                    distance = rect.y0 - target_y

                    if distance <= 250:

                        image_candidates.append(

                            (

                                distance,

                                rect,

                                xref,

                            )

                        )

        if not image_candidates:

            return None, None

        image_candidates.sort(

            key=lambda item: (

                item[0],

                -(

                    item[1].width

                    * item[1].height

                ),

            )

        )

        _, rect, xref = image_candidates[0]

        try:

            output_path = (
                (output_dir or self.job_pdf_dir)
                / (
                    f"page_{page_number:04d}"
                    f"_trademark.png"
                )
            )

            pixmap = page.get_pixmap(

                matrix=pymupdf.Matrix(3, 3),

                clip=rect,

                alpha=False,

            )

            pixmap.save(

                str(output_path)

            )

            return (

                str(output_path),

                [

                    float(rect.x0),

                    float(rect.y0),

                    float(rect.x1),

                    float(rect.y1),

                ],

            )

        except Exception:

            return None, None

    def _extract_owner(

        self,

        text: str,

    ) -> str:

        # ========================================================

        # 1. Extract raw (730) section

        # ========================================================

        match = re.search(

            r"\(730\)(.*?)(?=\(740\)|\(750\)|\(511\)|\(540\)|\(541\)|\Z)",

            text,

            re.IGNORECASE | re.DOTALL,

        )

        if not match:

            return ""

        value = match.group(1)

        # ========================================================

        # 2. Normalize whitespace

        # ========================================================

        value = re.sub(

            r"\s+",

            " ",

            value,

        ).strip()

        # ========================================================

        # 3. IMPORTANT:

        #    Remove everything before the first colon after (730)

        #

        #    Example:

        #    "ေလျှောက်ထားသူ၏ အမည်နှင့် နေရပ်လိပ်စာ :

        #     Consumer Goods Myanmar Limited"

        #

        #    becomes:

        #    "Consumer Goods Myanmar Limited"

        # ========================================================

        if ":" in value:

            value = value.split(":", 1)[1].strip()

        elif "：" in value:

            value = value.split("：", 1)[1].strip()

        # ========================================================

        # 4. Remove leading punctuation

        # ========================================================

        value = re.sub(

            r"^[\s:;,.\-]+",

            "",

            value,

        ).strip()

        # ========================================================

        # 5. Cut Phone / Email / Fax

        # ========================================================

        cut_patterns = [

            r"\bPhone\s*:",

            r"\bTel\s*:",

            r"\bTelephone\s*:",

            r"\bEmail\s*:",

            r"\bE-mail\s*:",

            r"\bFax\s*:",

        ]

        positions = []

        for pattern in cut_patterns:

            m = re.search(

                pattern,

                value,

                flags=re.IGNORECASE,

            )

            if m:

                positions.append(

                    m.start()

                )

        if positions:

            value = value[

                :min(positions)

            ].strip()

        # ========================================================

        # 6. Remove address after recognizable company suffix

        # ========================================================

        company_endings = [

            " COMPANY LIMITED",

            " PRIVATE LIMITED",

            " PTE LTD",

            " CO., LTD.",

            " CO., LTD",

            " CO LTD",

            " LIMITED",

            " LTD.",

            " LTD",

            " CORPORATION",

            " CORP.",

            " INC.",

            " INC",

            " N.V.",

            " S.A.",

        ]

        upper_value = value.upper()

        best_end = None

        for ending in company_endings:

            pos = upper_value.find(

                ending

            )

            if pos >= 0:

                end = pos + len(ending)

                if (

                    best_end is None

                    or end > best_end

                ):

                    best_end = end

        if best_end is not None:

            candidate = value[

                :best_end

            ].strip()

            if len(candidate) >= 4:

                value = candidate

        else:

            # ====================================================

            # 7. If no company suffix, remove obvious addresses

            # ====================================================

            address_patterns = [

                r"\bNo\.\s*\(?\d+",

                r"\bNO\.\s*\(?\d+",

                r"\b#\s*\d+",

                r"\b\d+\s+[A-Za-z][A-Za-z0-9.-]*\s+"

                r"(Road|Street|Avenue|Ave|Rd|St|Lane|Ln|"

                r"Boulevard|Blvd|Drive|Dr|Way)\b",

                r"\b\d+,\s*[A-Za-z][A-Za-z0-9.-]*\s+"

                r"(Road|Street|Avenue|Ave|Rd|St|Lane|Ln|"

                r"Boulevard|Blvd|Drive|Dr|Way)\b",

            ]

            for pattern in address_patterns:

                m = re.search(

                    pattern,

                    value,

                    flags=re.IGNORECASE,

                )

                if m:

                    value = value[

                        :m.start()

                    ].strip()

                    break

        # ========================================================

        # 8. Final whitespace cleanup

        # ========================================================

        value = re.sub(

            r"\s+",

            " ",

            value,

        ).strip()

        value = value.strip(

            " :;,.-"

        )

        return value

    def _extract_phone(

        self,

        text: str,

    ) -> str:

        matches = self.PHONE_RE.findall(

            text

        )

        cleaned = []

        for value in matches:

            digits = re.sub(

                r"\D",

                "",

                value,

            )

            if digits.startswith("95"):

                digits = "0" + digits[2:]

            if digits.startswith("9"):

                digits = "0" + digits

            if (

                digits.startswith("09")

                and 9 <= len(digits) <= 12

            ):

                cleaned.append(digits)

        # unique

        unique = []

        for value in cleaned:

            if value not in unique:

                unique.append(value)

        return ", ".join(unique[:5])

    def _extract_mark(

        self,

        text: str,

    ) -> str:
        match = re.search(

            r"\(541\).*?:\s*(.*?)"

            r"(?:\n|\r)",

            text,

            re.IGNORECASE,

        )

        if not match:

            return ""

        return re.sub(

            r"\s+",

            " ",

            match.group(1),

        ).strip()

    def _normalize_application(

        self,

        match,

    ) -> str:

        year = match.group(1)

        number = match.group(2)

        return (

            f"T/{year}/"

            f"{number.zfill(6)}"

        )

    def _application_keys(

        self,

        value: Any,

    ) -> List[str]:

        if value is None:

            return []

        text = str(value)

        results = []

        for match in self.APPLICATION_RE.finditer(

            text

        ):

            key = self._normalize_application(

                match

            )

            if key not in results:

                results.append(key)

        self._report_progress(100, "Analysis results saved.")
        return results

    def _get_client_rows(

        self,

    ) -> List[Dict[str, Any]]:

        if self.client_pdf_path:
            return self._client_pdf_records

        workbook = load_workbook(

            self.xlsx_path,

            data_only=True,

        )

        rows: List[Dict[str, Any]] = []

        try:

            for worksheet in workbook.worksheets:

                headers = None

                for row_index, row in enumerate(

                    worksheet.iter_rows(

                        values_only=True

                    ),

                    start=1,

                ):

                    values = list(row)

                    if headers is None:

                        header_map = {}

                        for index, value in enumerate(

                            values

                        ):

                            if value is None:

                                continue

                            header = (

                                str(value)

                                .strip()

                                .lower()

                            )

                            header_map[

                                header

                            ] = index

                        if (

                            "application no."

                            in header_map

                        ):

                            headers = header_map

                        continue

                    app_index = headers.get(

                        "application no."

                    )

                    if app_index is None:

                        continue

                    app_value = (

                        values[app_index]

                        if app_index < len(values)

                        else None

                    )

                    if not app_value:

                        continue

                    application_numbers = (

                        self._application_keys(

                            app_value

                        )

                    )

                    if not application_numbers:

                        continue

                    client = self._value_by_headers(

                        values,

                        headers,

                        [

                            "client",

                        ],

                    )

                    owner = self._value_by_headers(

                        values,

                        headers,

                        [

                            "owner",

                            "applicant",

                        ],

                    )

                    mark = self._value_by_headers(

                        values,

                        headers,

                        [
                            "mark",

                            "trademark",

                        ],

                    )

                    phone = self._value_by_headers(

                        values,

                        headers,

                        [

                            "phone",

                            "telephone",

                            "tel",

                        ],

                    )

                    rows.append(

                        {

                            "sheet":

                                worksheet.title,

                            "row":

                                row_index,

                            "application_no":

                                application_numbers,

                            "client":

                                self._clean_text(

                                    client

                                ),

                            "owner":

                                self._clean_text(

                                    owner

                                ),

                            "mark":

                                self._clean_text(

                                    mark

                                ),

                            "phone":

                                self._normalize_phone(

                                    phone

                                ),

                        }

                    )

        finally:

            workbook.close()

        return rows

    @staticmethod

    def _value_by_headers(

        values,

        headers,

        names,

    ):

        for name in names:

            index = headers.get(

                name.lower()

            )

            if index is not None:

                if index < len(values):

                    return values[index]

        return ""

    def _match_application_records(

        self,

        pdf_records: List[Dict[str, Any]],

    ) -> List[Dict[str, Any]]:

        client_rows = self._get_client_rows()

        pdf_map = {}

        for record in pdf_records:

            app = record.get(

                "application_no"

            )

            if app:

                pdf_map.setdefault(

                    app,

                    []

                ).append(record)

        results = []

        for client in client_rows:

            for app in client[

                "application_no"

            ]:

                for pdf in pdf_map.get(

                    app,

                    [],

                ):

                    results.append(

                        {

                            "type":

                                "APPLICATION",

                            "application_no":

                                app,

                            "pdf_page":

                                pdf["page"],

                            "pdf_owner":

                                pdf["owner"],

                            "pdf_mark":

                                pdf["mark"],

                            "client_owner":

                                client["owner"],

                            "client":

                                client["client"],

                            "client_mark":

                                client["mark"],

                            "sheet":

                                client["sheet"],

                            "row":

                                client["row"],

                        }

                    )

        return results
    
    def _match_company_records(

        self,

        pdf_records: List[Dict[str, Any]],
        client_logos: Optional[List[Dict[str, Any]]] = None,

    ) -> List[Dict[str, Any]]:

        client_rows = self._get_client_rows()

        client_logo_map = {}

        for logo in client_logos or []:

            sheet_name = str(

                logo.get("sheet") or ""

            ).strip()

            row_number = logo.get("row")

            if not sheet_name or row_number is None:

                continue

            try:

                key = (

                    sheet_name,

                    int(row_number),

                )

            except (TypeError, ValueError):

                continue

            client_logo_map[key] = logo
    # ------------------------------------------------------------

    # Helpers

    # ------------------------------------------------------------

        def normalize_application(value):

            if not value:

                return ""

            text = str(value).upper().strip()

            text = re.sub(r"\s+", "", text)

            text = re.sub(r"^MM/", "", text)

            match = re.search(r"T/(\d{4})/(\d+)", text)

            if match:

                return (

                    f"T/{match.group(1)}/"

                    f"{match.group(2).zfill(6)}"

                )

            return text

        def normalize_company(value):

            if not value:

                return ""

            text = str(value).upper()

        # Remove known Burmese address labels.

            text = re.sub(

                r"(ေလျှောက်ထားသူ၏|အမည်နှင့်|နေရပ်လိပ်စာ|နေရာလိပ်စာ|လိပ်စာ)",

                " ",

                text,

                flags=re.IGNORECASE,

            )

        # Normalize common company suffixes.

            replacements = [

                (r"\bCOMPANY\s+LIMITED\b", " CO LTD "),

                (r"\bPRIVATE\s+LIMITED\b", " PVT LTD "),

                (r"\bCO\.\s*,?\s*LTD\.?\b", " CO LTD "),

                (r"\bCO\s+LIMITED\b", " CO LTD "),

                (r"\bCORPORATION\b", " CORP "),

                (r"\bINCORPORATED\b", " INC "),

            ]

            for pattern, replacement in replacements:

                text = re.sub(

                    pattern,

                    replacement,

                    text,

                    flags=re.IGNORECASE,

                )

        # Keep English / numeric company identity.

            text = re.sub(

                r"[^A-Z0-9]+",

                " ",

                text,

            )

            text = re.sub(

                r"\s+",

                " ",

                text,

            ).strip()

            return text

        def company_core(value):

            """

            Build a stronger comparison key.

            This removes common legal suffixes so that:

                LIMITED

                LTD

                COMPANY LIMITED

                CO., LTD.

            do not create artificial differences.

            """

            normalized = normalize_company(value)

            if not normalized:

                return ""

            tokens = normalized.split()

            removable = {

                "COMPANY",

                "LIMITED",

                "LTD",

                "CO",

                "PVT",

                "PRIVATE",

                "CORPORATION",

                "CORP",

                "INC",

                "INCORPORATED",

            }

            tokens = [

                token

                for token in tokens

                if token not in removable

            ]

            return "".join(tokens)

        def application_from_row(row):

            value = row.get("application_no")

            if isinstance(value, list):

                for item in value:

                    normalized = normalize_application(item)

                    if normalized:

                        return normalized

                return ""

            return normalize_application(value)

    # ------------------------------------------------------------

    # Build client indexes

    # ------------------------------------------------------------

        client_by_application: Dict[str, List[Dict[str, Any]]] = {}

        client_by_company: Dict[str, List[Dict[str, Any]]] = {}

        client_by_company_core: Dict[str, List[Dict[str, Any]]] = {}

        for row_index, row in enumerate(client_rows):

            row["_company_row_index"] = row_index

            application_no = application_from_row(row)

            if application_no:

                client_by_application.setdefault(

                    application_no,

                    [],

                ).append(row)

            owner = row.get("owner") or ""

            company_key = normalize_company(owner)

            core_key = company_core(owner)

            if company_key:

                client_by_company.setdefault(

                    company_key,

                [],

                ).append(row)

            if core_key:

                client_by_company_core.setdefault(

                    core_key,

                    [],

                ).append(row)

        matches: List[Dict[str, Any]] = []

        seen = set()

        for pdf_record in pdf_records:

            pdf_application = normalize_application(

                pdf_record.get("application_no")

            )

            pdf_owner = pdf_record.get("owner") or ""

            pdf_company = normalize_company(pdf_owner)

            pdf_core = company_core(pdf_owner)

            application_candidates = []

            if pdf_application:

                application_candidates = client_by_application.get(

                    pdf_application,

                    [],

                )

            if application_candidates:

            # If multiple XLSX rows have same application number,

            # choose the first actual record only.

                client = application_candidates[0]

                client_owner = client.get("owner") or ""

            # Verify company when both sides have owner data.

                client_company = normalize_company(client_owner)

                company_verified = (

                    not pdf_company

                    or not client_company

                    or pdf_company == client_company

                    or company_core(pdf_owner) == company_core(client_owner)

                )

                if company_verified:

                    key = (

                        "application",

                        pdf_application,

                        client.get("_company_row_index"),

                    )

                    if key not in seen:

                        seen.add(key)

                        matches.append({

                            "match_type": "application",

                            "match_reason": "Exact application number match",

                            "application_no": pdf_application,

                            "pdf_application_no": pdf_record.get(

                                "application_no"

                            ),

                            "client_application_no": client.get(

                                "application_no"

                            ),

                            "pdf_page": pdf_record.get("page"),

                            "pdf_owner": pdf_record.get("owner"),

                            "client_owner": client.get("owner"),

                            "client": client.get("client"),

                            "mark": client.get("mark"),

                            "phone": client.get("phone"),

                            "sheet":
                                client.get("sheet"),

                            "row":
                                client.get("row"),

                            "pdf_image_path": pdf_record.get(

                                "image_path"

                            ),

                            "pdf_bbox": pdf_record.get("bbox"),

                            "client_image_path": client.get(

                                "image_path"

                            ),

                            "client_bbox": client.get(

                                "bbox"

                            ),

                            "confidence": 1.0,

                        })

                    # Exact application match wins.

                    continue

            company_candidates = []

            if pdf_company:

                company_candidates = client_by_company.get(

                    pdf_company,

                    [],

                )

            if not company_candidates and pdf_core:

                company_candidates = client_by_company_core.get(

                    pdf_core,

                    [],

                )

            if not company_candidates:

                continue

            pdf_mark = self._clean_text(

                pdf_record.get("mark") or ""

            ).upper()

            pdf_phone = self._normalize_phone(

                pdf_record.get("phone") or ""

            )

            best_client = None

            best_score = -1

            for client in company_candidates:

                score = 0

                client_mark = self._clean_text(

                    client.get("mark") or ""

                ).upper()

                client_phone = self._normalize_phone(

                    client.get("phone") or ""

                )

            # Same mark = strong secondary evidence.

                if (

                    pdf_mark

                    and client_mark

                    and (

                        pdf_mark == client_mark

                        or pdf_mark in client_mark

                        or client_mark in pdf_mark

                    )

                ):

                    score += 100

            # Same phone = strong secondary evidence.

                if (

                    pdf_phone

                    and client_phone

                    and pdf_phone == client_phone

                ):

                    score += 80

            # Prefer records with application numbers.

                if application_from_row(client):

                    score += 5

            # Prefer earlier stable row only when otherwise equal.

                if best_client is None or score > best_score:

                    best_client = client

                    best_score = score

            if best_client is None:

                continue

            client = best_client

            client_sheet = str(

                client.get("sheet") or ""

            ).strip()

            client_row = client.get("row")

            client_logo = None

            if client_sheet and client_row is not None:

                try:

                    client_logo = client_logo_map.get(

                        (

                            client_sheet,

                            int(client_row),

                        )

                    )

                except (TypeError, ValueError):

                    client_logo = None

            if client_logo:

                client = dict(client)

                client["image_path"] = client_logo.get(

                    "image_path"

                )

                client["bbox"] = client_logo.get(

                    "bbox"

                )

                client["logo_id"] = client_logo.get(

                    "id"

                )

                client["logo_width"] = client_logo.get(

                    "width"

                )

                client["logo_height"] = client_logo.get(

                    "height"

                )

            key = (

                "company",

                pdf_core or pdf_company,

                client.get("_company_row_index"),

            )

            if key in seen:

                continue

            seen.add(key)

            matches.append({

                "match_type": "company",

                "match_reason": "Exact company owner match",

                "application_no": pdf_application,

                "pdf_application_no": pdf_record.get(

                    "application_no"

                ),

                "client_application_no": client.get(

                    "application_no"

                ),

                "pdf_page": pdf_record.get("page"),

                "pdf_owner": pdf_record.get("owner"),

                "client_owner": client.get("owner"),

                "client": client.get("client"),

                "sheet": client.get("sheet"),

                "row": client.get("row"),

                "mark": client.get("mark"),

                "phone": client.get("phone"),

                "pdf_image_path": pdf_record.get(

                    "image_path"

                ),

                "pdf_bbox": pdf_record.get("bbox"),

                "client_image_path": client.get(

                    "image_path"

                ),

                "client_bbox": client.get(

                    "bbox"

                ),

                "confidence": 0.95,

            })

        return matches

    def _match_phone_records(

        self,

        pdf_records: List[Dict[str, Any]],

    ) -> List[Dict[str, Any]]:

        client_rows = self._get_client_rows()


        results = []

        for pdf in pdf_records:

            pdf_phones = self._phone_set(

                pdf.get("phone", "")

            )

            if not pdf_phones:

                continue

            for client in client_rows:

                client_phones = self._phone_set(

                    client.get("phone", "")

                )

                common = (

                    pdf_phones

                    & client_phones

                )

                if common:

                    results.append(

                        {

                            "type":

                                "PHONE",

                            "phones":

                                sorted(common),

                            "pdf_page":

                                pdf["page"],

                            "pdf_owner":

                                pdf["owner"],

                            "client_owner":

                                client["owner"],

                            "client":

                                client["client"],

                            "sheet":

                                client["sheet"],

                            "row":

                                client["row"],

                        }

                    )

        return results
    
    def _compare_logos(

        self,

        pdf_logos,

        client_logos,

    ):

        from pathlib import Path

        from app.services.similarity_engine import SimilarityEngine
        from app.services.logo_match.decision import decide_logo_match

        print("")

        print("------------------------------------------------------------")

        print("LOGO SIMILARITY DIAGNOSTIC")

        print("------------------------------------------------------------")

        if not pdf_logos:

            print("No PDF logos available.")

            return []

        if not client_logos:

            print("No client logos available.")

            return []

        print(f"PDF LOGOS    : {len(pdf_logos)}")

        print(f"CLIENT LOGOS : {len(client_logos)}")

        engine = SimilarityEngine(

            threshold=0.0

        )
        from app.services.ocr import extract_image_text, ocr_is_enabled

        use_ocr = ocr_is_enabled()
        ocr_text_cache: Dict[str, str] = {}

        def logo_text(logo: Dict[str, Any]) -> str:
            text = logo.get("mark") or ""
            if text or not use_ocr:
                return text
            image_path = logo.get("image_path")
            if not image_path:
                return ""
            if image_path not in ocr_text_cache:
                ocr_text_cache[image_path] = extract_image_text(image_path)
            return ocr_text_cache[image_path]

        results = []

        diagnostic_count = 0

        for pdf_logo in pdf_logos:

            for client_logo in client_logos:

                try:

                    result = engine.compare(

                        pdf_logo["image_path"],

                        client_logo["image_path"],

                    )

                except Exception as error:

                    print(

                        "COMPARE ERROR:",

                        pdf_logo.get("image_path"),

                        client_logo.get("image_path"),

                        error,

                    )

                    continue

                # Use the final visual score for ranking and thresholding.
                # The verifier confidence is diagnostic metadata and can be
                # lower than the score even when the visual comparison passes.
                similarity = float(
                    result.get(
                        "similarity_percent",
                        0.0,
                    )
                ) / 100.0

                candidate = {

                    "pdf_logo": pdf_logo,

                    "client_logo": client_logo,

                    "similarity": similarity,

                    "similarity_percent":

                        round(

                            similarity * 100,

                            2,

                        ),

                    "status":

                        result.get(

                            "status",

                            "UNKNOWN",

                        ),

                    "components":

                        result.get(

                            "components",

                            {},

                        ),

                }

                results.append(candidate)

        results.sort(

            key=lambda item:

                item["similarity"],

            reverse=True,

        )

        print("")

        print("------------------------------------------------------------")

        print("TOP LOGO SIMILARITY RESULTS")

        print("------------------------------------------------------------")

        for index, item in enumerate(

            results[:10],

            start=1,

        ):

            print(

                f"{index}. "

                f"{item['similarity_percent']}%"

            )

            print(

                "   PDF PAGE:",

                item["pdf_logo"].get("page"),

            )

            print(

                "   CLIENT ROW:",

                item["client_logo"].get("row"),

            )

            print(

                "   CLIENT OWNER:",

                item["client_logo"].get(

                    "client_owner"

                ),

            )

    # IMPORTANT:

    # Production threshold remains 82%.

        matched = []

        for item in results:
            visual_similarity = float(
                item.get(
                    "similarity_percent",
                    0.0,
                )
            ) / 100.0

            if visual_similarity < 0.82:
                continue

            pdf_logo = item.get("pdf_logo") or {}

            client_logo = item.get("client_logo") or {}

            pdf_mark = logo_text(pdf_logo)
            client_mark = logo_text(client_logo)

            decision = decide_logo_match(
                pdf_text=pdf_mark,
                client_text=client_mark,
                visual_similarity=visual_similarity,
                threshold=0.82,
            )
            if item.get("status") == "EXACT":
                decision["logo_match"] = True
                decision["visual_match"] = True
                decision["decision"] = "EXACT_VISUAL_MATCH"
                decision["reason"] = (
                    "The logo images are byte-identical."
                )

            item["logo_match"] = decision["logo_match"]

            item["text_match"] = decision["text_match"]

            item["visual_match"] = decision["visual_match"]

            item["visual_similarity"] = decision["visual_similarity"]

            item["decision"] = decision["decision"]

            item["decision_reason"] = decision["reason"]

            item["pdf_text"] = decision["pdf_text"]

            item["client_text"] = decision["client_text"]

            item["pdf_text_normalized"] = decision["pdf_normalized"]

            item["client_text_normalized"] = decision["client_normalized"]

            if decision["logo_match"]:

                matched.append(item)

        print("")

        print(

            "MATCHES >= 82%:",

            len(matched),

        )

        print(

            "------------------------------------------------------------"

        )

        return matched

    def _combine_matches(

        self,

        application_matches,

        company_matches,

        phone_matches,

        logo_matches,

    ) -> List[Dict[str, Any]]:

        results = []

        # Application

        for item in application_matches:

            results.append(

                {

                    "match_type":

                        "APPLICATION MATCH",

                    "application_no":

                        item[

                            "application_no"

                        ],

                    "pdf_page":

                        item["pdf_page"],

                    "company":

                        item["pdf_owner"]

                        or item["client_owner"],

                    "client":

                        item["client"],

                    "sheet":

                        item.get(

                            "sheet"

                        ),

                    "row":

                        item.get(

                            "row"

                        ),

                    "mark":
                        item["client_mark"],

                    "match_signals": [

                        "APPLICATION",

                    ],

                    "similarity_percent":

                        None,

                    "pdf_evidence":

                        {

                            "image_path":

                                item.get(

                                    "pdf_image_path"

                                ),

                            "bbox":

                                item.get(

                                    "pdf_bbox"

                                ),

                            "page":

                                item.get(

                                    "pdf_page"

                                ),

                        }

                        if item.get("pdf_image_path")

                        else None,

                    "client_evidence":

                        {

                            "image_path":

                                item.get(

                                    "client_image_path"

                                ),

                            "bbox":

                                item.get(

                                    "client_bbox"

                                ),

                        }

                        if item.get("client_image_path")

                        else None,

                }

            )

        # Company

        for item in company_matches:

            duplicate = any(

                existing.get(

                    "pdf_page"

                ) == item["pdf_page"]

                and existing.get(

                    "company"

                ) == item["pdf_owner"]

                for existing in results

            )

            if duplicate:

                continue

            results.append(

                {

                    "match_type":

                        "COMPANY MATCH",

                    "application_no":

                        (

                            item[

                                "application_no"

                            ]

                        ),

                    "pdf_page":

                        item["pdf_page"],

                    "company":

                        item["pdf_owner"],

                    "client":

                        item["client"],

                    
                    "sheet":

                        item.get(

                            "sheet"

                        ),

                    "row":

                        item.get(

                            "row"

                        ),

                    "mark":

                        "",

                    "match_signals": [

                        "COMPANY",

                    ],

                    "similarity_percent":

                        None,

                    "pdf_evidence":

                    {

                        "image_path":

                            item.get(

                                "pdf_image_path"

                        ),

                        "bbox":

                            item.get(

                                "pdf_bbox"

                            ),

                        "page":

                            item.get(

                                "pdf_page"

                            ),

                        }

                        if item.get(

                            "pdf_image_path"

                        )

                        else None,

                    "client_evidence":

                    {

                        "image_path":

                            item.get(

                                "client_image_path"

                            ),

                        "bbox":

                            item.get(

                                "client_bbox"

                            ),

                    }

                    if item.get(

                        "client_image_path"

                    )

                    else None,

                }

            )

        # Phone
        for item in phone_matches:
            duplicate = any(
                existing.get("pdf_page") == item.get("pdf_page")
                and existing.get("company") == item.get("pdf_owner")
                and existing.get("client") == item.get("client")
                for existing in results
            )

            if duplicate:
                continue

            results.append(
                {
                    "match_type": "PHONE MATCH",
                    "application_no": "",
                    "pdf_page": item.get("pdf_page"),
                    "company": item.get("pdf_owner"),
                    "client": item.get("client"),
                    "sheet": item.get("sheet"),
                    "row": item.get("row"),
                    "mark": "",
                    "match_signals": ["PHONE"],
                    "phones": item.get("phones", []),
                    "similarity_percent": None,
                    "pdf_evidence": None,
                    "client_evidence": None,
                }
            )

        # Logo
        for item in logo_matches:
            pdf = item.get("pdf_logo") or item.get("pdf") or {}
            client = item.get("client_logo") or item.get("client") or {}

            pdf_image_path = pdf.get("image_path")
            client_image_path = client.get("image_path")

            results.append(
                {
                    "match_type": "LOGO MATCH",
                    "application_no": pdf.get("application_no", ""),
                    "pdf_page": pdf.get("page"),
                    "company": pdf.get("owner", ""),
                    "client": client.get("client", ""),
                    "sheet": client.get("sheet"),
                    "row": client.get("row"),
                    "pdf_sheet": pdf.get("sheet"),
                    "pdf_row": pdf.get("row"),
                    "mark": client.get("mark") or pdf.get("mark", ""),
                    "match_signals": ["LOGO"],
                    "similarity_percent": item.get("similarity_percent"),
                    "similarity": item.get("similarity"),
                    "visual_similarity": item.get("visual_similarity"),
                    "logo_match": item.get("logo_match"),
                    "text_match": item.get("text_match"),
                    "visual_match": item.get("visual_match"),
                    "decision": item.get("decision"),
                    "decision_reason": item.get("decision_reason"),
                    "similarity_status": item.get("status", "UNKNOWN"),
                    "similarity_components": item.get("components", {}),
                    "pdf_evidence": (
                        {
                            "image_path": pdf_image_path,
                            "bbox": pdf.get("bbox"),
                            "page": pdf.get("page"),
                        }
                        if pdf_image_path
                        else None
                    ),
                    "client_evidence": (
                        {
                            "image_path": client_image_path,
                            "bbox": client.get("bbox"),
                            "sheet": client.get("sheet"),
                            "row": client.get("row"),
                        }
                        if client_image_path
                        else None
                    ),
                    "client_page": client.get("page"),
                    "_logo_match": item,
                }
            )

        return results

    def _render_match_evidence(
        self,
        match: Dict[str, Any],
        index: int,
    ):
        """Render visual evidence safely for a conflict match."""

        match_type = str(match.get("match_type") or "MATCH").upper()
        logo_match = match.get("_logo_match")

        pdf_info: Dict[str, Any] = {}
        client_info: Dict[str, Any] = {}
        similarity_percent = match.get("similarity_percent")

        # ------------------------------------------------------------
        # LOGO MATCH
        # ------------------------------------------------------------
        if match_type == "LOGO MATCH" and isinstance(logo_match, dict):
            pdf_info = (
                logo_match.get("pdf_logo")
                or logo_match.get("pdf")
                or {}
            )
            client_info = (
                logo_match.get("client_logo")
                or logo_match.get("client")
                or {}
            )
            similarity_percent = logo_match.get(
                "similarity_percent",
                similarity_percent,
            )

        # ------------------------------------------------------------
        # OTHER MATCH TYPES
        # ------------------------------------------------------------
        else:
            pdf_evidence = match.get("pdf_evidence")
            client_evidence = match.get("client_evidence")

            if isinstance(pdf_evidence, dict):
                pdf_info = dict(pdf_evidence)
            elif isinstance(pdf_evidence, str):
                pdf_info = {"image_path": pdf_evidence}

            if isinstance(client_evidence, dict):
                client_info = dict(client_evidence)
            elif isinstance(client_evidence, str):
                client_info = {"image_path": client_evidence}

            if not pdf_info:
                pdf_info = {
                    "image_path": match.get("pdf_image_path"),
                    "bbox": match.get("pdf_bbox"),
                    "page": match.get("pdf_page"),
                    "application_no": match.get("application_no"),
                }

            if not client_info:
                client_info = {
                    "image_path": match.get("client_image_path"),
                    "bbox": match.get("client_bbox"),
                    "sheet": match.get("sheet"),
                    "row": match.get("row"),
                }

        # ------------------------------------------------------------
        # Source paths
        # ------------------------------------------------------------
        pdf_path = pdf_info.get("image_path")
        client_path = client_info.get("image_path")

        pdf_page = pdf_info.get("page") or match.get("pdf_page")
        pdf_bbox = pdf_info.get("bbox")

        # Do not attempt to render empty evidence.
        if not pdf_path and not client_path:
            match.pop("logo_match", None)
            return

        self.evidence_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ------------------------------------------------------------
        # Evidence label
        # ------------------------------------------------------------
        if similarity_percent is not None:
            label = f"{match.get('application_no', '')} {similarity_percent}%".strip()
        else:
            label = match_type

        # ------------------------------------------------------------
        # PDF evidence
        # ------------------------------------------------------------
        pdf_output = None

        if pdf_path and pdf_page:
            pdf_output = self.evidence_dir / (
                f"match{index:04d}pdf_page{int(pdf_page):04d}.png"
            )

            try:
                self.draw_pdf_evidence(
                    page_number=int(pdf_page),
                    bbox=pdf_bbox,
                    output_path=pdf_output,
                    label=label,
                )
            except Exception:
                # Fallback to extracted trademark image.
                try:
                    source_image = cv2.imread(
                        str(pdf_path),
                        cv2.IMREAD_COLOR,
                    )
                    if source_image is not None:
                        cv2.imwrite(
                            str(pdf_output),
                            source_image,
                        )
                    else:
                        pdf_output = None
                except Exception:
                    pdf_output = None
        elif pdf_path:
            pdf_output = self.evidence_dir / (
                f"match{index:04d}_source_logo.png"
            )
            try:
                self._draw_client_evidence(
                    image_path=str(pdf_path),
                    output_path=pdf_output,
                    label=label,
                )
            except Exception:
                try:
                    source_image = cv2.imread(
                        str(pdf_path),
                        cv2.IMREAD_COLOR,
                    )
                    if source_image is not None:
                        cv2.imwrite(str(pdf_output), source_image)
                    else:
                        pdf_output = None
                except Exception:
                    pdf_output = None

        # ------------------------------------------------------------
        # Client XLSX evidence
        # ------------------------------------------------------------
        client_output = None

        if client_path:
            client_output = self.evidence_dir / (
                f"match{index:04d}_client_logo.png"
            )

            try:
                self._draw_client_evidence(
                    image_path=str(client_path),
                    output_path=client_output,
                    label=label,
                )
            except Exception:
                # Fallback to original client image.
                try:
                    source_image = cv2.imread(
                        str(client_path),
                        cv2.IMREAD_COLOR,
                    )
                    if source_image is not None:
                        cv2.imwrite(
                            str(client_output),
                            source_image,
                        )
                    else:
                        client_output = None
                except Exception:
                    client_output = None

        # ------------------------------------------------------------
        # Return generated evidence paths
        # ------------------------------------------------------------
        if pdf_output and pdf_output.exists():
            match["pdf_evidence"] = str(pdf_output)
        elif not match.get("pdf_evidence"):
            match["pdf_evidence"] = None

        if client_output and client_output.exists():
            match["client_evidence"] = str(client_output)
        elif not match.get("client_evidence"):
            match["client_evidence"] = None

        # Internal metadata must never reach the API response.
        match.pop("_logo_match", None)

    def _draw_pdf_evidence(

        self,

        page_number: int,

        bbox,

        output_path: Path,

        label: str,

    ):

        with pymupdf.open(

            self.pdf_path

        ) as document:

            page = document[

                page_number - 1

            ]

            zoom = 2.0

            pixmap = page.get_pixmap(

                matrix=pymupdf.Matrix(

                    zoom,

                    zoom,

                ),

                alpha=False,

            )

            image = np.frombuffer(

                pixmap.samples,

                dtype=np.uint8,

            )

            image = image.reshape(

                pixmap.height,

                pixmap.width,

                pixmap.n,

            )

            if pixmap.n == 4:

                image = cv2.cvtColor(

                    image,

                    cv2.COLOR_RGBA2BGR,

                )

            else:

                image = cv2.cvtColor(

                    image,

                    cv2.COLOR_RGB2BGR,

                )

            if bbox:

                x0, y0, x1, y1 = bbox

                x0 = int(x0 * zoom)

                y0 = int(y0 * zoom)

                x1 = int(x1 * zoom)

                y1 = int(y1 * zoom)

                x0 = max(

                    0,

                    min(
                        x0,

                        image.shape[1] - 1,

                    ),

                )

                y0 = max(

                    0,

                    min(

                        y0,

                        image.shape[0] - 1,

                    ),

                )

                x1 = max(

                    0,

                    min(

                        x1,

                        image.shape[1] - 1,

                    ),

                )

                y1 = max(

                    0,

                    min(

                        y1,

                        image.shape[0] - 1,

                    ),

                )

                cv2.rectangle(

                    image,

                    (x0, y0),

                    (x1, y1),

                    (0, 0, 255),

                    5,

                )

                center = (

                    (x0 + x1) // 2,

                    (y0 + y1) // 2,

                )

                axes = (

                    max(

                        20,

                        (x1 - x0) // 2,

                    ),

                    max(

                        20,

                        (y1 - y0) // 2,

                    ),

                )

                cv2.ellipse(

                    image,

                    center,

                    axes,

                    0,

                    0,

                    360,

                    (0, 0, 255),

                    4,

                )

                cv2.putText(

                    image,

                    label,

                    (

                        max(10, x0),

                        max(30, y0 - 10),

                    ),

                    cv2.FONT_HERSHEY_SIMPLEX,

                    0.8,

                    (0, 0, 255),

                    2,

                    cv2.LINE_AA,

                )

            cv2.imwrite(

                str(output_path),

                image,

            )

    def _draw_client_evidence(

        self,

        image_path: str,

        output_path: Path,

        label: str,

    ):

        image = cv2.imread(

            image_path,

            cv2.IMREAD_COLOR,

        )

        if image is None:

            return

        height, width = image.shape[:2]

        margin_x = max(

            4,

            int(width * 0.03),

        )

        margin_y = max(

            4,

            int(height * 0.03),

        )

        x0 = margin_x

        y0 = margin_y

        x1 = width - margin_x

        y1 = height - margin_y

        cv2.rectangle(

            image,

            (x0, y0),

            (x1, y1),

            (0, 0, 255),

            4,

        )

        center = (

            (x0 + x1) // 2,

            (y0 + y1) // 2,

        )

        axes = (

            max(10, (x1 - x0) // 2),

            max(10, (y1 - y0) // 2),

        )

        cv2.ellipse(

            image,

            center,

            axes,

            0,

            0,

            360,

            (0, 0, 255),

            3,

        )

        cv2.putText(

            image,

            label,

            (

                10,

                max(25, y0 - 8),

            ),

            cv2.FONT_HERSHEY_SIMPLEX,

            0.7,

            (0, 0, 255),

            2,

            cv2.LINE_AA,

        )

        cv2.imwrite(

            str(output_path),

            image,

        )
    @staticmethod

    def _clean_text(

        value: Any,

    ) -> str:

        if value is None:

            return ""

        return re.sub(

            r"\s+",

            " ",

            str(value),

        ).strip()

    @staticmethod

    def _normalize_company(

        value: Any,

    ) -> str:

        text = (

            AnalysisService._clean_text(

                value

            )

            .upper()

        )

        text = re.sub(

            r"[^A-Z0-9]",

            "",

            text,

        )

        replacements = {

            "COMPANYLIMITED":

                "CO",

            "COMPANYLTD":

                "CO",

            "LIMITED":

                "LTD",

            "CORPORATION":

                "CORP",

        }

        for old, new in replacements.items():

            text = text.replace(

                old,

                new,

            )

        return text

    @staticmethod

    def _normalize_phone(

        value: Any,

    ) -> str:

        if value is None:

            return ""

        digits = re.sub(

            r"\D",

            "",

            str(value),

        )

        if digits.startswith("95"):

            digits = "0" + digits[2:]

        if digits.startswith("9"):

            digits = "0" + digits

        return digits

    @staticmethod

    def _phone_set(

        value: Any,

    ) -> set:

        if not value:

            return set()

        text = str(value)

        values = re.split(

            r"[,;/|]+",

            text,

        )

        result = set()

        for item in values:

            normalized = (

                AnalysisService

                ._normalize_phone(

                    item

                )

            )

            if (

                normalized.startswith("09")

                and 9 <= len(normalized) <= 12

            ):

                result.add(normalized)

        return result

    def _get_client_records_count(self) -> int:

        from openpyxl import load_workbook

        workbook = load_workbook(

            self.xlsx_path,

            read_only=True,

            data_only=True,

        )

        count = 0

        try:

            for worksheet in workbook.worksheets:

                for row in worksheet.iter_rows(values_only=True):

                    values = [

                        value

                        for value in row

                        if value is not None and str(value).strip()

                    ]

                    if not values:

                        continue

                    first_value = str(values[0]).strip().lower()

                # Skip header row

                    if first_value in {

                        "no",

                        "no.",

                        "number",

                        "id",

                        "serial",

                    }:

                        continue

                    count += 1

            return count

        finally:

            workbook.close()