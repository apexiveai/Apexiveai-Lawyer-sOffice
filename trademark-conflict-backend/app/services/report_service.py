from __future__ import annotations

from html import escape
import json

from datetime import datetime, timezone

from pathlib import Path

from typing import Any

from reportlab.lib import colors

from reportlab.lib.enums import TA_CENTER, TA_LEFT

from reportlab.lib.pagesizes import A4

from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

from reportlab.lib.units import mm

from reportlab.platypus import (

    BaseDocTemplate,

    Frame,

    Image,

    PageBreak,

    PageTemplate,

    Paragraph,

    Spacer,

    Table,

    TableStyle,

)

from sqlalchemy import select

from app.core.config import EVIDENCE_DIR

from app.db.database import SessionLocal

from app.models.review import Review

class TrademarkConflictReportService:

    """

    Generates a human-review-aware trademark conflict

    investigation report from the persisted analysis result

    and review database.

    """

    def __init__(self, job_id: str):

        self.job_id = job_id.strip()

        if not self.job_id:

            raise ValueError("job_id is required.")

        self.job_dir = (EVIDENCE_DIR / self.job_id).resolve()

        self.result_file = self.job_dir / "analysis_result.json"

        self.report_file = (

            self.job_dir / "trademark_conflict_investigation_report.pdf"

        )

    # ---------------------------------------------------------

    # PUBLIC

    # ---------------------------------------------------------

    def generate(self) -> Path:

        if not self.job_dir.exists():

            raise FileNotFoundError(

                f"Job evidence directory not found: {self.job_id}"

            )

        if not self.result_file.exists():

            raise FileNotFoundError(

                "analysis_result.json not found for this job."

            )

        result = self._load_result()

        reviews = self._load_reviews()

        cases = self._build_cases(result, reviews)

        self._build_pdf(

            result=result,

            cases=cases,

        )

        return self.report_file

    # ---------------------------------------------------------

    # DATA

    # ---------------------------------------------------------

    def _load_result(self) -> dict[str, Any]:

        with self.result_file.open(

            "r",

            encoding="utf-8",

        ) as file:

            data = json.load(file)

        if not isinstance(data, dict):

            raise ValueError(

                "analysis_result.json must contain an object."

            )

        return data

    def _load_reviews(self) -> dict[str, Review]:

        session = SessionLocal()

        try:

            rows = session.execute(

                select(Review).where(

                    Review.job_id == self.job_id

                )

            ).scalars().all()

            return {

                row.conflict_id: row

                for row in rows

            }

        finally:

            session.close()

    # ---------------------------------------------------------

    # CASE GROUPING

    # ---------------------------------------------------------

    @staticmethod

    def _value(

        match: dict[str, Any],

        keys: list[str],

        default: str = "",

    ) -> str:

        for key in keys:

            value = match.get(key)

            if value is None:

                continue

            text = str(value).strip()

            if text:

                return text

        return default

    @classmethod

    def _conflict_id(

        cls,

        match: dict[str, Any],

    ) -> str:

        application = cls._value(

            match,

            [

                "application_no",

                "application_number",

                "application",

                "app_no",

                "number",

            ],

            "NO-APPLICATION",

        )

        page = cls._value(

            match,

            [

                "page",

                "pdf_page",

                "page_number",

            ],

            "NO-PAGE",

        )

        company = cls._value(

            match,

            [

                "company",

                "company_name",

                "applicant",

                "applicant_name",

                "owner",

                "client_owner",

            ],

            "NO-COMPANY",

        )

        return "|".join(

            [

                application,

                page,

                company,

            ]

        ).strip().upper()

    @classmethod

    def _build_cases(

        cls,

        result: dict[str, Any],

        reviews: dict[str, Review],

    ) -> list[dict[str, Any]]:

        raw_matches = result.get("matches") or []

        if not isinstance(raw_matches, list):

            raw_matches = []

        groups: dict[str, dict[str, Any]] = {}

        for match in raw_matches:

            if not isinstance(match, dict):

                continue

            conflict_id = cls._conflict_id(match)

            if conflict_id not in groups:

                groups[conflict_id] = {

                    "case_id": conflict_id,

                    "application": cls._value(

                        match,

                        [

                            "application_no",

                            "application_number",

                            "application",

                            "app_no",

                            "number",

                        ],

                        "N/A",

                    ),

                    "page": cls._value(

                        match,

                        [

                            "page",

                            "pdf_page",

                            "page_number",

                        ],

                        "N/A",

                    ),

                    "company": cls._value(

                        match,

                        [

                            "company",

                            "company_name",

                            "applicant",

                            "applicant_name",

                            "owner",

                            "client_owner",

                        ],

                        "N/A",

                    ),

                    "signals": [],

                    "matches": [],

                }

            group = groups[conflict_id]

            signal = cls._value(

                match,

                [

                    "match_type",

                    "matchType",

                    "type",

                ],

                "CONFLICT",

            ).upper()

            if signal not in group["signals"]:

                group["signals"].append(signal)

            group["matches"].append(match)

        cases = []

        for conflict_id, case in groups.items():

            review = reviews.get(conflict_id)

            if review:
                status = (

                    str(review.status or "PENDING")

                    .strip()

                    .upper()

                )

                comment = review.comment or ""

                reviewer = review.reviewer or ""

                reviewed_at = review.reviewed_at

            else:

                status = "PENDING"

                comment = ""

                reviewer = ""

                reviewed_at = None

            case["status"] = (

                status

                if status in {

                    "PENDING",

                    "CONFIRMED",

                    "REJECTED",

                }

                else "PENDING"

            )

            case["comment"] = comment

            case["reviewer"] = reviewer

            case["reviewed_at"] = reviewed_at

            cases.append(case)

        cases.sort(

            key=lambda item: (

                str(item["page"]),

                str(item["application"]),

            )

        )

        return cases

    # ---------------------------------------------------------

    # EVIDENCE

    # ---------------------------------------------------------

    def _resolve_evidence_path(

        self,

        evidence: Any,

    ) -> Path | None:

        if not evidence:

            return None

        value = str(evidence).strip()

        if not value:

            return None
        
        path = Path(value)

        if path.exists() and path.is_file():

            return path

        # URL-style evidence path:

        # /evidence/{job_id}/{filename}

        marker = f"/evidence/{self.job_id}/"

        if marker in value:

            filename = value.split(marker, 1)[1].split("?", 1)[0]

            candidate = (

                self.job_dir / Path(filename).name

            ).resolve()

            try:

                candidate.relative_to(

                    self.job_dir

                )

            except ValueError:

                return None

            if candidate.exists() and candidate.is_file():

                return candidate

        # Relative filename

        candidate = (

            self.job_dir / Path(value).name

        ).resolve()

        try:

            candidate.relative_to(

                self.job_dir

            )

        except ValueError:

            return None

        if candidate.exists() and candidate.is_file():

            return candidate

        return None

    @classmethod

    def _match_value(

        cls,

        match: dict[str, Any],

        government: bool,

    ) -> str:

        if government:

            keys = [

                "pdf_value",

                "government_value",

                "source_value",

                "matched_pdf_value",

                "pdf_match",

                "government_match",

                "value",

            ]

        else:

            keys = [

                "client_value",

                "xlsx_value",

                "client_match",

                "matched_client_value",

                "client",

            ]

        return cls._value(

            match,

            keys,

            "—",
)

    def _build_pdf(

        self,

        result: dict[str, Any],

        cases: list[dict[str, Any]],

    ) -> None:

        self.report_file.parent.mkdir(

            parents=True,

            exist_ok=True,

        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(

            "ReportTitle",

            parent=styles["Title"],

            fontName="Helvetica-Bold",

            fontSize=20,

            leading=24,

            alignment=TA_CENTER,

            textColor=colors.HexColor("#D6A84F"),

            spaceAfter=8,

        )

        subtitle_style = ParagraphStyle(

            "ReportSubtitle",

            parent=styles["Normal"],

            fontName="Helvetica",

            fontSize=9,

            leading=13,

            alignment=TA_CENTER,

            textColor=colors.HexColor("#777777"),

            spaceAfter=18,

        )

        section_style = ParagraphStyle(

            "Section",

            parent=styles["Heading2"],

            fontName="Helvetica-Bold",

            fontSize=12,

            leading=15,

            textColor=colors.HexColor("#222222"),

            spaceBefore=8,

            spaceAfter=8,

        )

        body_style = ParagraphStyle(

            "Body",

            parent=styles["BodyText"],

            fontName="Helvetica",

            fontSize=8.5,

            leading=12,

            textColor=colors.HexColor("#333333"),

        )

        small_style = ParagraphStyle(

            "Small",

            parent=body_style,

            fontSize=7.5,

            leading=10,

        )

        label_style = ParagraphStyle(

            "Label",

            parent=body_style,

            fontName="Helvetica-Bold",

            fontSize=7,

            leading=9,

            textColor=colors.HexColor("#777777"),

        )

        value_style = ParagraphStyle(

            "Value",

            parent=body_style,

            fontName="Helvetica-Bold",

            fontSize=8.5,

            leading=11,
)
        doc = BaseDocTemplate(

            str(self.report_file),

            pagesize=A4,

            rightMargin=16 * mm,

            leftMargin=16 * mm,

            topMargin=18 * mm,

            bottomMargin=18 * mm,

            title=(

                "Trademark Conflict "

                "Investigation Report"

            ),

            author="Apexive AI",

        )

        frame = Frame(

            doc.leftMargin,

            doc.bottomMargin,

            doc.width,

            doc.height,

            id="normal",

        )

        doc.addPageTemplates(

            [

                PageTemplate(

                    id="report",

                    frames=frame,

                    onPage=self._draw_footer,

                )

            ]

        )

        story: list[Any] = []

        # -----------------------------------------------------

        # COVER / HEADER

        # -----------------------------------------------------

        story.append(

            Spacer(1, 18 * mm)

        )

        story.append(

            Paragraph(

                "APEXIVE AI",

                subtitle_style,

            )

        )

        story.append(

            Paragraph(

                "Trademark Conflict<br/>"

                "Investigation Report",

                title_style,

            )

        )

        story.append(

            Paragraph(

                "AI-assisted trademark conflict "

                "analysis and human review record",

                subtitle_style,

            )

        )

        story.append(

            Spacer(1, 5 * mm)

        )

        job_table = Table(

            [

                [

                    Paragraph(

                        "JOB ID",

                        label_style,

                    ),

                    Paragraph(

                        self.job_id,

                        value_style,

                    ),

                ],
[

                    Paragraph(

                        "GENERATED",

                        label_style,

                    ),

                    Paragraph(

                        self._now_string(),

                        value_style,

                    ),

                ],

            ],

            colWidths=[

                35 * mm,

                125 * mm,

            ],

        )

        job_table.setStyle(

            TableStyle(

                [

                    (

                        "BACKGROUND",

                        (0, 0),

                        (-1, -1),

                        colors.HexColor("#F7F7F7"),

                    ),

                    (

                        "BOX",

                        (0, 0),

                        (-1, -1),

                        0.6,

                        colors.HexColor("#DDDDDD"),

                    ),

                    (

                        "INNERGRID",

                        (0, 0),

                        (-1, -1),

                        0.3,

                        colors.HexColor("#E5E5E5"),

                    ),

                    (

                        "VALIGN",

                        (0, 0),

                        (-1, -1),

                        "MIDDLE",

                    ),

                    (

                        "LEFTPADDING",

                        (0, 0),

                        (-1, -1),

                        8,

                    ),

                    (

                        "RIGHTPADDING",

                        (0, 0),

                        (-1, -1),

                        8,

                    ),

                    (

                        "TOPPADDING",

                        (0, 0),

                        (-1, -1),

                        7,

                    ),

                    (

                        "BOTTOMPADDING",

                        (0, 0),

                        (-1, -1),

                        7,

                    ),

                ]

            )

        )

        story.append(job_table)
        story.append(
            Paragraph("Jurisdiction and source citations", section_style)
        )
        jurisdiction_scope = result.get("jurisdiction_scope") or {}
        class_scope = result.get("nice_class_scope") or {}
        if isinstance(jurisdiction_scope, dict):
            left_jurisdiction = jurisdiction_scope.get("left")
            right_jurisdiction = jurisdiction_scope.get("right")
        else:
            left_jurisdiction = right_jurisdiction = None
        if isinstance(class_scope, dict):
            left_classes = class_scope.get("left") or []
            right_classes = class_scope.get("right") or []
        else:
            left_classes = right_classes = []
        if not left_jurisdiction and not right_jurisdiction:
            left_jurisdiction = right_jurisdiction = result.get("jurisdiction")
        if not left_classes and not right_classes:
            left_classes = right_classes = result.get("nice_classes") or []
        left_class_text = ", ".join(
            escape(str(value)) for value in left_classes
        ) if isinstance(left_classes, list) else escape(str(left_classes))
        right_class_text = ", ".join(
            escape(str(value)) for value in right_classes
        ) if isinstance(right_classes, list) else escape(str(right_classes))
        left_jurisdiction_text = escape(str(left_jurisdiction or "Not specified"))
        right_jurisdiction_text = escape(str(right_jurisdiction or "Not specified"))
        story.append(
            Paragraph(
                f"First record: {left_jurisdiction_text}, "
                f"Nice classes {left_class_text or 'Not specified'}<br/>"
                f"Second record: {right_jurisdiction_text}, "
                f"Nice classes {right_class_text or 'Not specified'}",
                body_style,
            )
        )
        scope_assessment = result.get("goods_services_assessment")
        if isinstance(scope_assessment, dict):
            disposition = escape(
                str(scope_assessment.get("disposition") or "NEEDS_REVIEW")
            )
            score = scope_assessment.get("score")
            review_reasons = scope_assessment.get("review_reasons") or []
            reason_text = "; ".join(
                escape(str(reason)) for reason in review_reasons
            )
            story.append(
                Paragraph(
                    "Goods/services scope assessment (advisory): "
                    f"{disposition}"
                    + (
                        f" &nbsp;|&nbsp; Similarity score: {float(score):.3f}"
                        if isinstance(score, (int, float))
                        else ""
                    )
                    + (f"<br/>Review notes: {reason_text}" if reason_text else "")
                    + "<br/>This scope score is an analytical aid, not a legal conclusion.",
                    body_style,
                )
            )
        source_citations = result.get("source_citations") or []
        citation_rows = [[
            Paragraph("SOURCE", label_style),
            Paragraph("REGISTRY RECORD", label_style),
            Paragraph("URL", label_style),
            Paragraph("RETRIEVED", label_style),
        ]]
        for citation in source_citations:
            if not isinstance(citation, dict):
                continue
            citation_rows.append(
                [
                    Paragraph(escape(str(citation.get("source_name") or "—")), value_style),
                    Paragraph(
                        escape(str(citation.get("source_record_id") or "—")),
                        value_style,
                    ),
                    Paragraph(
                        (
                            f'<link href="{escape(str(citation["source_url"]), quote=True)}">'
                            f'{escape(str(citation["source_url"]))}</link>'
                            if str(citation.get("source_url", "")).startswith(
                                ("https://", "http://")
                            )
                            else "—"
                        ),
                        value_style,
                    ),
                    Paragraph(escape(str(citation.get("retrieved_at") or "—")), value_style),
                ]
            )
        if len(citation_rows) > 1:
            source_table = Table(
                citation_rows,
                colWidths=[30 * mm, 28 * mm, 75 * mm, 30 * mm],
                repeatRows=1,
            )
            source_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F0E6D2")),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            story.append(source_table)
        else:
            story.append(
                Paragraph(
                    "No external registry citation metadata was supplied for this analysis.",
                    body_style,
                )
            )
        story.append(
            Spacer(1, 12 * mm)
)
        story.append(

            Paragraph(

                "1. Investigation Summary",

                section_style,

            )

        )

        metrics = [

            (

                "PDF PAGES",

                result.get("pdf_pages", 0),

            ),

            (

                "CLIENT RECORDS",

                result.get("client_records", 0),

            ),

            (

                "APPLICATION MATCHES",

                result.get(

                    "application_matches",

                    0,

                ),

            ),

            (

                "LOGO MATCHES",

                result.get("logo_matches", 0),

            ),

            (

                "COMPANY MATCHES",

                result.get(

                    "company_matches",

                    0,

                ),

            ),

            (

                "PHONE MATCHES",

                result.get(

                    "phone_matches",

                    0,

                ),

            ),

        ]

        metric_rows = []

        for index in range(0, len(metrics), 3):

            row = []

            for label, value in metrics[index:index + 3]:

                row.append(

                    Table(

                        [

                            [

                                Paragraph(

                                    label,

                                    label_style,

                                )

                            ],

                            [

                                Paragraph(

                                    str(value),

                                    ParagraphStyle(

                                        "MetricValue",

                                        parent=value_style,

                                        fontSize=16,

                                        leading=18,

                                        textColor=colors.HexColor(

                                            "#222222"

                                        ),

                                    ),

                                )

                            ],

                        ],

                        colWidths=[51 * mm],

                    )
)
            while len(row) < 3:

                row.append("")

            metric_rows.append(row)

        metrics_table = Table(

            metric_rows,

            colWidths=[

                53 * mm,

                53 * mm,

                53 * mm,

            ],

            hAlign="LEFT",

        )

        metrics_table.setStyle(

            TableStyle(

                [

                    (

                        "BOX",

                        (0, 0),

                        (-1, -1),

                        0.5,

                        colors.HexColor("#DDDDDD"),

                    ),

                    (

                        "INNERGRID",

                        (0, 0),

                        (-1, -1),

                        0.35,

                        colors.HexColor("#E5E5E5"),

                    ),

                    (

                        "VALIGN",

                        (0, 0),

                        (-1, -1),

                        "TOP",

                    ),

                    (

                        "LEFTPADDING",

                        (0, 0),

                        (-1, -1),

                        7,

                    ),

                    (

                        "RIGHTPADDING",

                        (0, 0),

                        (-1, -1),

                        7,

                    ),

                    (

                        "TOPPADDING",

                        (0, 0),

                        (-1, -1),

                        8,

                    ),

                    (

                        "BOTTOMPADDING",

                        (0, 0),

                        (-1, -1),

                        8,

                    ),

                ]

            )

        )

        story.append(metrics_table)

        # -----------------------------------------------------

        # CASE SUMMARY

        # -----------------------------------------------------

        story.append(

            Paragraph(

                "2. Conflict Case Summary",

                section_style,

            )

        )

        confirmed = sum(

            1

            for case in cases

            if case["status"] == "CONFIRMED"

        )

        rejected = sum(

            1

            for case in cases

            if case["status"] == "REJECTED"
)
        pending = len(cases) - confirmed - rejected

        summary_data = [

            [

                Paragraph("TOTAL CASES", label_style),

                Paragraph("PENDING", label_style),

                Paragraph("CONFIRMED", label_style),

                Paragraph("REJECTED", label_style),

            ],

            [

                Paragraph(str(len(cases)), value_style),

                Paragraph(str(pending), value_style),

                Paragraph(str(confirmed), value_style),

                Paragraph(str(rejected), value_style),

            ],

        ]

        summary_table = Table(

            summary_data,

            colWidths=[

                42 * mm,

                42 * mm,

                42 * mm,

                42 * mm,

            ],

        )

        summary_table.setStyle(

            TableStyle(

                [

                    (

                        "BACKGROUND",

                        (0, 0),

                        (-1, 0),

                        colors.HexColor("#F3F3F3"),

                    ),

                    (

                        "BOX",

                        (0, 0),

                        (-1, -1),

                        0.5,

                        colors.HexColor("#DDDDDD"),

                    ),

                    (

                        "INNERGRID",

                        (0, 0),

                        (-1, -1),

                        0.35,

                        colors.HexColor("#E5E5E5"),

                    ),

                    (

                        "ALIGN",

                        (0, 0),

                        (-1, -1),

                        "CENTER",

                    ),

                    (

                        "TOPPADDING",

                        (0, 0),

                        (-1, -1),

                        8,

                    ),

                    (

                        "BOTTOMPADDING",

                        (0, 0),

                        (-1, -1),

                        8,

                    ),

                ]

            )

        )

        story.append(summary_table)

        story.append(PageBreak())

        # -----------------------------------------------------

        # CASES

        # -----------------------------------------------------

        story.append(

            Paragraph(

                "3. Conflict Cases",

                section_style,

            )

        )

        if not cases:

            story.append(

                Paragraph(

                    "No conflict cases were identified.",

                    body_style,

                )
)
        for case_index, case in enumerate(

            cases,

            start=1,

        ):

            story.append(

                Paragraph(

                    f"Case {case_index:03d}",

                    ParagraphStyle(

                        "CaseHeading",

                        parent=section_style,

                        fontSize=11,

                        textColor=colors.HexColor(

                            "#D6A84F"

                        ),

                    ),

                )

            )

            case_info = Table(

                [

                    [

                        Paragraph(

                            "APPLICATION",

                            label_style,

                        ),

                        Paragraph(

                            str(

                                case["application"]

                            ),

                            value_style,

                        ),

                    ],

                    [

                        Paragraph(

                            "PDF PAGE",

                            label_style,

                        ),

                        Paragraph(

                            str(case["page"]),

                            value_style,

                        ),

                    ],

                    [

                        Paragraph(

                            "COMPANY",

                            label_style,

                        ),

                        Paragraph(

                            str(case["company"]),

                            value_style,

                        ),

                    ],

                    [

                        Paragraph(

                            "REVIEW STATUS",

                            label_style,

                        ),

                        Paragraph(

                            str(case["status"]),

                            value_style,

                        ),

                    ],

                ],

                colWidths=[

                    35 * mm,

                    125 * mm,

                ],

            )

            case_info.setStyle(

                TableStyle(

                    [

                        (

                            "BACKGROUND",

                            (0, 0),

                            (0, -1),

                            colors.HexColor("#F7F7F7"),

                        ),

                        (

                            "BOX",

                            (0, 0),

                            (-1, -1),

                            0.5,

                            colors.HexColor("#DDDDDD"),

                        ),

                        (

                            "INNERGRID",

                            (0, 0),

                            (-1, -1),

                            0.3,

                            colors.HexColor("#E5E5E5"),

                        ),

                        (

                            "VALIGN",

                            (0, 0),

                            (-1, -1),

                            "MIDDLE",

                        ),

                        (

                            "LEFTPADDING",

                            (0, 0),

                            (-1, -1),

                            7,

                        ),

(

                            "RIGHTPADDING",

                            (0, 0),

                            (-1, -1),

                            7,

                        ),

                        (

                            "TOPPADDING",

                            (0, 0),

                            (-1, -1),

                            6,

                        ),

                        (

                            "BOTTOMPADDING",

                            (0, 0),

                            (-1, -1),

                            6,

                        ),

                    ]

                )

            )

            story.append(case_info)

            story.append(Spacer(1, 4 * mm))

            signals = ", ".join(

                case["signals"]

            ) or "CONFLICT"

            story.append(

                Paragraph(

                    f"<b>Conflict Signals:</b> "

                    f"{self._escape(signals)}",

                    body_style,

                )

            )

            story.append(

                Spacer(1, 3 * mm)

            )

            # Evidence table

            evidence_rows = [

                [

                    Paragraph("TYPE", label_style),

                    Paragraph(

                        "GOVERNMENT / PDF",

                        label_style,

                    ),

                    Paragraph(

                        "CLIENT",

                        label_style,

                    ),

                ]

            ]

            evidence_images = []

            for match in case["matches"]:

                signal = self._value(

                    match,

                    [

                        "match_type",

                        "matchType",

                        "type",

                    ],

                    "CONFLICT",

                ).upper()

                government_value = (

                    self._match_value(

                        match,

                        True,

                    )

                )

                client_value = (

                    self._match_value(

                        match,

                        False,

                    )

                )

                evidence_rows.append(
[

                        Paragraph(

                            self._escape(signal),

                            small_style,

                        ),

                        Paragraph(

                            self._escape(

                                government_value

                            ),

                            small_style,

                        ),

                        Paragraph(

                            self._escape(

                                client_value

                            ),

                            small_style,

                        ),

                    ]

                )

                pdf_evidence = self._resolve_evidence_path(

                    match.get("pdf_evidence")

                )

                client_evidence = self._resolve_evidence_path(

                    match.get("client_evidence")

                )

                evidence_images.append(

                    (

                        signal,

                        pdf_evidence,

                        client_evidence,

                    )

                )

            evidence_table = Table(

                evidence_rows,

                colWidths=[

                    34 * mm,

                    63 * mm,

                    63 * mm,

                ],

                repeatRows=1,

            )

            evidence_table.setStyle(

                TableStyle(

                    [

                        (

                            "BACKGROUND",

                            (0, 0),

                            (-1, 0),

                            colors.HexColor("#F3F3F3"),

                        ),

                        (

                            "BOX",

                            (0, 0),

                            (-1, -1),

                            0.5,

                            colors.HexColor("#DDDDDD"),

                        ),

                        (

                            "INNERGRID",

                            (0, 0),

                            (-1, -1),

                            0.3,

                            colors.HexColor("#E5E5E5"),

                        ),

                        (

                            "VALIGN",

                            (0, 0),

                            (-1, -1),

                            "TOP",

                        ),

                        (

                            "LEFTPADDING",

                            (0, 0),

                            (-1, -1),

                            6,

                        ),

                        (

                            "RIGHTPADDING",

                            (0, 0),

                            (-1, -1),

                            6,

                        ),

                        (

                            "TOPPADDING",

                            (0, 0),

                            (-1, -1),

                            6,

                        ),

                        (

                            "BOTTOMPADDING",

                            (0, 0),

                            (-1, -1),

                            6,

                        ),

                    ]

                )

            )

            story.append(evidence_table)
            
            image_count = 0

            for (

                signal,

                pdf_image,

                client_image,

            ) in evidence_images:

                if not pdf_image and not client_image:

                    continue

                story.append(

                    Spacer(1, 3 * mm)

                )

                story.append(

                    Paragraph(

                        f"Evidence — "

                        f"{self._escape(signal)}",

                        label_style,

                    )

                )

                image_cells = []

                if pdf_image:

                    try:

                        image_cells.append(

                            Image(

                                str(pdf_image),

                                width=75 * mm,

                                height=52 * mm,

                                kind="proportional",

                            )

                        )

                    except Exception:

                        image_cells.append(

                            Paragraph(

                                "PDF evidence unavailable.",

                                small_style,

                            )

                        )

                else:

                    image_cells.append(

                        Paragraph(

                            "No PDF evidence.",

                            small_style,

                        )

                    )

                if client_image:

                    try:

                        image_cells.append(

                            Image(

                                str(client_image),

                                width=75 * mm,

                                height=52 * mm,

                                kind="proportional",

                            )

                        )

                    except Exception:

                        image_cells.append(

                            Paragraph(

                                "Client evidence unavailable.",

                                small_style,

                            )

                        )

                else:

                    image_cells.append(

                        Paragraph(

                            "No client evidence.",

                            small_style,

                        )

                    )

                image_table = Table(

                    [image_cells],

                    colWidths=[

                        78 * mm,

                        78 * mm,

                    ],
)
                image_table.setStyle(

                    TableStyle(

                        [

                            (

                                "BOX",

                                (0, 0),

                                (-1, -1),

                                0.4,

                                colors.HexColor("#DDDDDD"),

                            ),

                            (

                                "INNERGRID",

                                (0, 0),

                                (-1, -1),

                                0.3,

                                colors.HexColor("#EEEEEE"),

                            ),

                            (

                                "VALIGN",

                                (0, 0),

                                (-1, -1),

                                "MIDDLE",

                            ),

                            (

                                "ALIGN",

                                (0, 0),

                                (-1, -1),

                                "CENTER",

                            ),

                            (

                                "TOPPADDING",

                                (0, 0),

                                (-1, -1),

                                5,

                            ),

                            (

                                "BOTTOMPADDING",

                                (0, 0),

                                (-1, -1),

                                5,

                            ),

                        ]

                    )

                )

                story.append(image_table)

                image_count += 1

            # Human review

            story.append(

                Spacer(1, 4 * mm)

            )

            story.append(

                Paragraph(

                    "Human Review",

                    label_style,

                )

            )

            review_data = [

                [

                    Paragraph(

                        "STATUS",

                        label_style,

                    ),

                    Paragraph(

                        self._escape(

                            case["status"]

                        ),

                        value_style,

                    ),

                ],
[

                    Paragraph(

                        "REVIEWER",

                        label_style,

                    ),

                    Paragraph(

                        self._escape(

                            case["reviewer"]

                            or "—"

                        ),

                        small_style,

                    ),

                ],

                [

                    Paragraph(

                        "REVIEWED AT",

                        label_style,

                    ),

                    Paragraph(

                        self._escape(

                            self._format_datetime(

                                case["reviewed_at"]

                            )

                        ),

                        small_style,

                    ),

                ],

                [

                    Paragraph(

                        "COMMENT",

                        label_style,

                    ),

                    Paragraph(

                        self._escape(

                            case["comment"]

                            or "—"

                        ),

                        small_style,

                    ),

                ],

            ]

            review_table = Table(

                review_data,

                colWidths=[

                    35 * mm,

                    125 * mm,

                ],

            )

            review_table.setStyle(

                TableStyle(

                    [

                        (

                            "BACKGROUND",

                            (0, 0),

                            (0, -1),

                            colors.HexColor("#F7F7F7"),

                        ),

                        (

                            "BOX",

                            (0, 0),

                            (-1, -1),

                            0.5,

                            colors.HexColor("#DDDDDD"),

                        ),

                        (

                            "INNERGRID",

                            (0, 0),

                            (-1, -1),

                            0.3,

                            colors.HexColor("#E5E5E5"),

                        ),

                        (

                            "VALIGN",

                            (0, 0),

                            (-1, -1),

                            "TOP",

                        ),

                        (

                            "LEFTPADDING",

                            (0, 0),

                            (-1, -1),

                            7,
),
(

                            "RIGHTPADDING",

                            (0, 0),

                            (-1, -1),

                            7,

                        ),

                        (

                            "TOPPADDING",

                            (0, 0),

                            (-1, -1),

                            6,

                        ),

                        (

                            "BOTTOMPADDING",

                            (0, 0),

                            (-1, -1),

                            6,

                        ),

                    ]

                )

            )

            story.append(review_table)

            if case_index != len(cases):

                story.append(

                    Spacer(1, 7 * mm)

                )

        # -----------------------------------------------------

        # FINAL NOTE

        # -----------------------------------------------------

        story.append(PageBreak())

        story.append(

            Paragraph(

                "4. Investigation Record",

                section_style,

            )

        )

        story.append(

            Paragraph(

                "This report records the persisted AI analysis "

                "results and the human review decisions associated "

                "with the selected trademark conflict investigation. "

                "The report does not re-run the underlying analysis.",

                body_style,

            )

        )

        story.append(

            Spacer(1, 8 * mm)

        )

        story.append(

            Paragraph(

                "Generated by Apexive AI "

                "Trademark Intelligence",

                ParagraphStyle(

                    "Final",

                    parent=body_style,

                    alignment=TA_CENTER,

                    textColor=colors.HexColor(

                        "#777777"

                    ),

                ),

            )

        )

        doc.build(story)

    @staticmethod
    def _escape(value: Any) -> str:

        text = str(value)

        return (

            text.replace("&", "&amp;")

            .replace("<", "&lt;")

            .replace(">", "&gt;")

        )

    @staticmethod

    def _now_string() -> str:

        return datetime.now(

            timezone.utc

        ).strftime(

            "%Y-%m-%d %H:%M UTC"

        )

    @staticmethod

    def _format_datetime(

        value: Any,

    ) -> str:

        if not value:

            return "—"

        if isinstance(value, datetime):

            return value.strftime(

                "%Y-%m-%d %H:%M UTC"

            )

        return str(value)

    @staticmethod

    def _draw_footer(

        canvas,

        document,

    ) -> None:

        canvas.saveState()

        width, _ = A4

        canvas.setStrokeColor(

            colors.HexColor("#DDDDDD")

        )

        canvas.setLineWidth(0.4)

        canvas.line(

            document.leftMargin,

            12 * mm,

            width - document.rightMargin,

            12 * mm,

        )

        canvas.setFont(

            "Helvetica",

            7,
)
        canvas.setFillColor(

            colors.HexColor("#888888")

        )

        canvas.drawString(

            document.leftMargin,

            7 * mm,

            "Apexive AI — Trademark Intelligence",

        )

        canvas.drawRightString(

            width - document.rightMargin,

            7 * mm,

            f"Page {document.page}",

        )

        canvas.restoreState()