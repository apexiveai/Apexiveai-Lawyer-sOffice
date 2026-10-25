from __future__ import annotations

from dataclasses import dataclass, asdict

from pathlib import Path

from typing import Any

import cv2

import pymupdf

import numpy as np

from app.services.logo_detector import LogoDetector
@dataclass

class BoundingBox:

    # Pixel coordinates in rendered image

    x: int

    y: int

    width: int

    height: int

    # PDF coordinates in points

    pdf_x: float

    pdf_y: float

    pdf_width: float

    pdf_height: float

    def to_dict(self):

        return asdict(self)

@dataclass

class LogoCandidate:

    candidate_id: str

    page_number: int

    image_path: str

    crop_path: str | None

    bbox: BoundingBox

    area_ratio: float

    aspect_ratio: float

    confidence: float

    source: str

    def to_dict(self):

        return asdict(self)

class PDFLogoDetector:

    """

    Production-oriented PDF page renderer and

    visual candidate detector.

    Coordinate systems:

        PDF:

            points

            origin = top-left for PyMuPDF page coordinates

        Render:

            pixels

            origin = top-left

    Conversion:

        pixel_x = pdf_x * zoom

        pixel_y = pdf_y * zoom

        pdf_x = pixel_x / zoom

        pdf_y = pixel_y / zoom

    """

    def __init__(

        self,

        pdf_path: str,

        output_dir: str,

        dpi: int = 200,

    ):

        self.pdf_path = Path(pdf_path)

        self.output_dir = Path(output_dir)

        self.dpi = dpi

        self.zoom = dpi / 72.0

        self.render_dir = (

            self.output_dir / "pages"

        )

        self.crop_dir = (

            self.output_dir / "logo_candidates"

        )

        self.render_dir.mkdir(

            parents=True,

            exist_ok=True,

        )

        self.crop_dir.mkdir(

            parents=True,

            exist_ok=True,

        )
        self.logo_detector = LogoDetector()
    # =========================================================

    # PUBLIC

    # =========================================================

    def process(self) -> dict[str, Any]:

        if not self.pdf_path.exists():

            raise FileNotFoundError(

                f"PDF not found: {self.pdf_path}"

            )

        candidates: list[LogoCandidate] = []

        with pymupdf.open(

            str(self.pdf_path)

        ) as document:

            total_pages = len(document)

            for page_index in range(

                total_pages

            ):

                page_number = (

                    page_index + 1

                )

                page_result = self.process_page(

                    document,

                    page_index,

                )

                candidates.extend(

                    page_result["candidates"]

                )

        return {

            "pdf": self.pdf_path.name,

            "dpi": self.dpi,

            "zoom": self.zoom,

            "pages": total_pages,

            "candidates": [

                candidate.to_dict()

                for candidate in candidates

            ],

        }
    def filter_logo_candidates(

        self,

        image,

        candidates,

    ):

        filtered = []

        for candidate in candidates:

            pixel_bbox = (

                self.pdf_bbox_to_pixel_bbox(

                    candidate.bbox

                )

            )

            result = (

                self.logo_detector.analyze_candidate(

                    image,

                    pixel_bbox,

                )

            )

            candidate.confidence = (

                result["score"]

            )

            if result["is_logo"]:

                filtered.append(

                    candidate

                )

        return filtered    

    def process_page(

        self,

        document: pymupdf.Document,

        page_index: int,

    ) -> dict:

        page = document[page_index]

        page_number = page_index + 1

        rendered = self.render_page(

            page,

            page_number,

        )

        image = rendered["image"]

        candidates = []

    # ---------------------------------------------------------

    # Embedded images

    # ---------------------------------------------------------

        embedded = self.detect_embedded_images(

            document,

            page,

            page_number,

            image,

        )

        candidates.extend(

            embedded

        )

    # ---------------------------------------------------------

    # Vector regions

    # ---------------------------------------------------------

        vector_candidates = (

            self.detect_visual_regions(

                page,

                page_number,

                image,

            )

        )

        candidates.extend(

            vector_candidates

        )

        contour_candidates = (

            self.detect_contour_candidates(

                page_number,

                image,

            )

        )

        candidates.extend(

            contour_candidates

        )

        candidates = (

            self.remove_duplicates(

                candidates

            )

        )

        candidates = (

            self.filter_logo_candidates(

                image,

                candidates,

            )

        )

        evidence_dir = (

            self.output_dir

            / "evidence"

        )

        evidence_dir.mkdir(

            parents=True,

            exist_ok=True,

        )

        for index, candidate in enumerate(

            candidates,

            start=1,

        ):

            candidate.crop_path = (

                self.save_candidate_crop(

                    image,

                    candidate,

                )

            )

            evidence_name = (

                f"page_{page_number:04d}_"

                f"logo_{index:04d}.png"

            )
            evidence_path = (

                self.output_dir / "evidence" / evidence_name

            )

            evidence_path.parent.mkdir(

                parents=True,

                exist_ok=True,

            )

            self.render_candidate_evidence(

                rendered["path"],

                candidate,

                evidence_path,

            )

        return {

            "page": page_number,

            "render": {

                key: value

                for key, value in rendered.items()

                if key != "image"

            },

            "candidates": candidates,

        }

    def render_page(

        self,

        page: pymupdf.Page,

        page_number: int,

    ) -> dict[str, Any]:

        matrix = pymupdf.Matrix(

            self.zoom,

            self.zoom,

        )

        pixmap = page.get_pixmap(

            matrix=matrix,

            alpha=False,

            colorspace=pymupdf.csRGB,

        )

        output_path = (

            self.render_dir

            / f"page_{page_number:04d}.png"

        )

        pixmap.save(

            str(output_path)

        )

        image = cv2.imread(

            str(output_path),

            cv2.IMREAD_COLOR,

        )

        if image is None:

            raise RuntimeError(

                f"Unable to load rendered page: "

                f"{output_path}"

            )

        return {

            "page": page_number,

            "path": str(output_path),

            "width": pixmap.width,

            "height": pixmap.height,

            "pdf_width": page.rect.width,

            "pdf_height": page.rect.height,

            "dpi": self.dpi,

            "zoom": self.zoom,

            "image": image,

        }

    # =========================================================

    # EMBEDDED PDF IMAGES

    # =========================================================

    def detect_embedded_images(

        self,

        document: pymupdf.Document,

        page: pymupdf.Page,

        page_number: int,

        rendered_image,

    ) -> list[LogoCandidate]:

        results = []

        image_list = page.get_images(

            full=True

        )

        for index, image_info in enumerate(

            image_list,

            start=1,

        ):

            xref = image_info[0]

            try:

                rects = page.get_image_rects(

                    image_info

                )

            except Exception:

                continue

            if not rects:

                continue

            for occurrence, rect in enumerate(

                rects,

                start=1,

            ):

                bbox = self.pdf_rect_to_bbox(

                    rect

                )

                pixel_bbox = (

                    self.pdf_bbox_to_pixel_bbox(

                        bbox

                    )

                )

                if not self.valid_bbox(

                    pixel_bbox,

                    rendered_image,

                ):

                    continue

                confidence = (

                    self.embedded_image_confidence(

                        pixel_bbox,

                        rendered_image,

                    )

                )

                candidate_id = (

                    f"pdf_p{page_number}_"

                    f"img{index}_"

                    f"occ{occurrence}"

                )

                results.append(

                    LogoCandidate(

                        candidate_id=(
                        candidate_id

                        ),

                        page_number=page_number,

                        image_path="",

                        crop_path=None,

                        bbox=bbox,

                        area_ratio=(

                            self.area_ratio(

                                pixel_bbox,

                                rendered_image,

                            )

                        ),

                        aspect_ratio=(

                            self.aspect_ratio(

                                pixel_bbox

                            )

                        ),

                        confidence=confidence,

                        source="embedded_image",

                    )

                )

        return results

    # =========================================================

    # VECTOR / DRAWING DETECTION

    # =========================================================

    def detect_visual_regions(

        self,

        page: pymupdf.Page,

        page_number: int,

        rendered_image,

    ) -> list[LogoCandidate]:

        results = []

        try:

            drawings = page.get_drawings()

        except Exception:

            drawings = []

        for index, drawing in enumerate(

            drawings,

            start=1,

        ):

            rect = drawing.get(

                "rect"

            )

            if rect is None:

                continue

            bbox = self.pdf_rect_to_bbox(

                rect

            )

            pixel_bbox = (

                self.pdf_bbox_to_pixel_bbox(

                    bbox

                )

            )

            if not self.valid_bbox(

                pixel_bbox,

                rendered_image,

            ):

                continue

            x, y, w, h = pixel_bbox

            area = w * h

            if area < 400:

                continue

            ratio = (

                max(w, h)

                / max(min(w, h), 1)

            )

            # Very long lines are not logo candidates.

            if ratio > 8.0:

                continue

            confidence = (

                self.visual_region_confidence(

                    pixel_bbox,

                    rendered_image,

                )

            )

            if confidence < 0.20:

                continue

            results.append(

                LogoCandidate(

                    candidate_id=(

                        f"pdf_p{page_number}_"

                        f"vector_{index}"

                    ),

                    page_number=page_number,

                    image_path="",

                    crop_path=None,

                    bbox=bbox,

                    area_ratio=(

                        self.area_ratio(

                            pixel_bbox,

                            rendered_image,

                        )

                    ),

                    aspect_ratio=(

                        self.aspect_ratio(

                            pixel_bbox

                        )

                    ),

                    confidence=confidence,

                    source="vector_region",

                )

            )

        return results

    # =========================================================

    # RASTER CONTOUR DETECTION

    # =========================================================

    def detect_contour_candidates(

        self,

        page_number: int,

        image,

    ) -> list[LogoCandidate]:

        results = []

        gray = cv2.cvtColor(

            image,

            cv2.COLOR_BGR2GRAY,

        )

        # Slight denoise

        blurred = cv2.GaussianBlur(

            gray,

            (5, 5),

            0,

        )

        # Edge detection

        edges = cv2.Canny(

            blurred,

            50,

            150,

        )

        kernel = cv2.getStructuringElement(

            cv2.MORPH_RECT,

            (5, 5),

        )
        edges = cv2.morphologyEx(

            edges,

            cv2.MORPH_CLOSE,

            kernel,

            iterations=2,

        )

        contours, _ = cv2.findContours(

            edges,

            cv2.RETR_EXTERNAL,

            cv2.CHAIN_APPROX_SIMPLE,

        )

        image_height, image_width = (

            image.shape[:2]

        )

        page_area = (

            image_width

            * image_height

        )

        candidate_index = 0

        for contour in contours:

            x, y, w, h = cv2.boundingRect(

                contour

            )

            area = w * h

            if area < 900:

                continue

            if area > (

                page_area * 0.20

            ):

                continue

            aspect = (

                max(w, h)

                / max(min(w, h), 1)

            )

            if aspect > 7.0:

                continue

            fill_ratio = (

                cv2.contourArea(contour)

                / max(area, 1)

            )

            # Reject tiny text-like fragments.

            if fill_ratio < 0.01:

                continue

            if not self.is_reasonable_logo_region(

                x,

                y,

                w,

                h,

                image_width,

                image_height,

            ):

                continue

            pdf_bbox = (

                self.pixel_bbox_to_pdf_bbox(

                    (x, y, w, h)

                )

            )

            candidate_index += 1

            confidence = (

                self.contour_confidence(

                    w,

                    h,

                    fill_ratio,

                    image_width,

                    image_height,

                )

            )

            if confidence < 0.25:

                continue

            results.append(

                LogoCandidate(

                    candidate_id=(

                        f"pdf_p{page_number}_"

                        f"contour_{candidate_index}"

                    ),

                    page_number=page_number,

                    image_path="",

                    crop_path=None,

                    bbox=pdf_bbox,

                    area_ratio=(

                        area / page_area

                    ),

                    aspect_ratio=aspect,

                    confidence=confidence,

                    source="contour",

                )

            )

        return results

    # =========================================================

    # COORDINATE SYSTEM

    # =========================================================

    def pdf_rect_to_bbox(

        self,

        rect: pymupdf.Rect,

    ) -> BoundingBox:

        return BoundingBox(

            x=float(rect.x0),

            y=float(rect.y0),

            width=float(rect.width),

            height=float(rect.height),

            pdf_x=float(rect.x0),

            pdf_y=float(rect.y0),

            pdf_width=float(rect.width),

            pdf_height=float(rect.height),

        )

    def pdf_bbox_to_pixel_bbox(

        self,

        bbox: BoundingBox,

    ) -> tuple[int, int, int, int]:

        x = round(

            bbox.pdf_x * self.zoom

        )

        y = round(

            bbox.pdf_y * self.zoom

        )

        width = round(

            bbox.pdf_width * self.zoom

        )

        height = round(

            bbox.pdf_height * self.zoom

        )

        return (

            x,

            y,

            width,

            height,

        )

    def pixel_bbox_to_pdf_bbox(

        self,

        bbox: tuple[int, int, int, int],

    ) -> BoundingBox:

        x, y, width, height = bbox

        pdf_x = (

            x / self.zoom

        )

        pdf_y = (

            y / self.zoom

        )

        pdf_width = (

            width / self.zoom

        )

        pdf_height = (

            height / self.zoom

        )

        return BoundingBox(

            x=x,

            y=y,
            width=width,

            height=height,

            pdf_x=pdf_x,

            pdf_y=pdf_y,

            pdf_width=pdf_width,

            pdf_height=pdf_height,

        )

    # =========================================================

    # VALIDATION / SCORING

    # =========================================================

    @staticmethod

    def valid_bbox(

        bbox,

        image,

    ) -> bool:

        x, y, w, h = bbox

        height, width = image.shape[:2]

        if w <= 5 or h <= 5:

            return False

        if x >= width or y >= height:

            return False

        if x + w <= 0 or y + h <= 0:

            return False

        return True

    @staticmethod

    def area_ratio(

        bbox,

        image,

    ) -> float:

        x, y, w, h = bbox

        height, width = image.shape[:2]

        return (

            (w * h)

            / max(width * height, 1)

        )

    @staticmethod

    def aspect_ratio(

        bbox,

    ) -> float:

        _, _, w, h = bbox

        return (

            max(w, h)

            / max(min(w, h), 1)

        )

    def embedded_image_confidence(

        self,

        bbox,

        image,

    ) -> float:

        _, _, w, h = bbox

        area = self.area_ratio(

            bbox,

            image,

        )

        aspect = self.aspect_ratio(

            bbox

        )

        score = 0.80

        if 0.0005 <= area <= 0.15:

            score += 0.10

        if aspect <= 4:

            score += 0.10

        return min(score, 1.0)

    def visual_region_confidence(

        self,

        bbox,

        image,

    ) -> float:

        _, _, w, h = bbox

        aspect = (

            max(w, h)

            / max(min(w, h), 1)

        )

        score = 0.40

        if aspect <= 3:

            score += 0.25

        if aspect <= 2:

            score += 0.15

        if w >= 30 and h >= 30:

            score += 0.10

        return min(score, 1.0)

    @staticmethod

    def contour_confidence(

        width: int,

        height: int,

        fill_ratio: float,

        image_width: int,

        image_height: int,

    ) -> float:

        aspect = (

            max(width, height)

            / max(min(width, height), 1)

        )

        score = 0.20

        if aspect <= 4:

            score += 0.20

        if aspect <= 2.5:

            score += 0.15

        if fill_ratio >= 0.08:

            score += 0.15

        if width >= 40 and height >= 40:

            score += 0.15

        area_ratio = (

            width * height

            / max(

                image_width * image_height,

                1,

            )

        )

        if (

            0.0005

            <= area_ratio

            <= 0.10

        ):

            score += 0.15

        return min(score, 1.0)

    @staticmethod

    def is_reasonable_logo_region(

        x,

        y,

        w,

        h,

        image_width,

        image_height,

    ) -> bool:

        if w < 30 or h < 30:

            return False

        if w > image_width * 0.6:

            return False

        if h > image_height * 0.6:

            return False

        return True

    # =========================================================

    # DUPLICATE REMOVAL

    # =========================================================

    def remove_duplicates(

        self,

        candidates: list[LogoCandidate],

    ) -> list[LogoCandidate]:

        selected = []

        # High confidence first

        candidates.sort(

            key=lambda item: item.confidence,

            reverse=True,

        )

        for candidate in candidates:

            candidate_pixel_bbox = (

                self.pdf_bbox_to_pixel_bbox(

                    candidate.bbox

                )

            )

            duplicate = False

            for existing in selected:

                existing_pixel_bbox = (

                    self.pdf_bbox_to_pixel_bbox(

                        existing.bbox

                    )
                )

                iou = self.calculate_iou(

                    candidate_pixel_bbox,

                    existing_pixel_bbox,

                )

                if iou >= 0.70:

                    duplicate = True

                    break

            if not duplicate:

                selected.append(

                    candidate

                )

        return selected

    @staticmethod

    def calculate_iou(

        bbox_a,

        bbox_b,

    ) -> float:

        ax, ay, aw, ah = bbox_a

        bx, by, bw, bh = bbox_b

        ax2 = ax + aw

        ay2 = ay + ah

        bx2 = bx + bw

        by2 = by + bh

        ix1 = max(ax, bx)

        iy1 = max(ay, by)

        ix2 = min(ax2, bx2)

        iy2 = min(ay2, by2)

        iw = max(

            0,

            ix2 - ix1,

        )

        ih = max(

            0,

            iy2 - iy1,

        )

        intersection = iw * ih

        area_a = aw * ah

        area_b = bw * bh

        union = (

            area_a

            + area_b

            - intersection

        )

        if union <= 0:

            return 0.0

        return (

            intersection

            / union

        )

    # =========================================================

    # CROP

    # =========================================================

    def save_candidate_crop(

        self,

        image,

        candidate: LogoCandidate,

    ) -> str | None:

        pixel_bbox = (

            self.pdf_bbox_to_pixel_bbox(

                candidate.bbox

            )

        )

        x, y, w, h = pixel_bbox

        height, width = image.shape[:2]

        # Padding for logo evidence

        padding_x = max(

            int(w * 0.10),

            8,

        )

        padding_y = max(

            int(h * 0.10),

            8,

        )

        x1 = max(

            0,

            x - padding_x,

        )

        y1 = max(

            0,

            y - padding_y,

        )

        x2 = min(

            width,

            x + w + padding_x,

        )

        y2 = min(

            height,

            y + h + padding_y,

        )

        crop = image[

            y1:y2,

            x1:x2,

        ]

        if crop.size == 0:

            return None

        filename = (

            f"{candidate.candidate_id}.png"

        )

        output_path = (

            self.crop_dir

            / filename

        )

        cv2.imwrite(

            str(output_path),

            crop,

        )

        candidate.image_path = str(

            output_path

        )

        return str(output_path)

    def render_candidate_evidence(

    self,

    image_source,

    candidate,

    output_path,

):

        """

        Create a lightweight evidence image around the detected logo.

        Uses the pixel coordinates already stored in candidate.bbox.

        The output is intentionally cropped around the candidate so

        evidence generation stays fast and frontend-friendly.

        """

        if isinstance(image_source, (str, Path)):

            image = cv2.imread(str(image_source))

            if image is None:

                raise RuntimeError(

                    f"Unable to read rendered page image: {image_source}"

                )

        else:

            image = image_source.copy()

        if image is None or image.size == 0:

            raise RuntimeError("Invalid image supplied for evidence rendering")

        image_height, image_width = image.shape[:2]

        bbox = candidate.bbox

        x = int(round(bbox.x))

        y = int(round(bbox.y))

        w = int(round(bbox.width))

        h = int(round(bbox.height))

    # Safety normalization

        x = max(0, min(x, image_width - 1))

        y = max(0, min(y, image_height - 1))

        w = max(1, w)

        h = max(1, h)

        x2 = min(image_width, x + w)

        y2 = min(image_height, y + h)

    # ---------------------------------------------------------

    # 3. Add padding around detected logo

    # ---------------------------------------------------------

        padding_x = max(30, int(w * 0.75))

        padding_y = max(30, int(h * 0.75))

        crop_x1 = max(0, x - padding_x)

        crop_y1 = max(0, y - padding_y)

        crop_x2 = min(image_width, x2 + padding_x)

        crop_y2 = min(image_height, y2 + padding_y)

        evidence = image[

            crop_y1:crop_y2,

            crop_x1:crop_x2,

        ].copy()

        if evidence.size == 0:

            raise RuntimeError(

                "Evidence crop is empty"

            )

        local_x1 = x - crop_x1

        local_y1 = y - crop_y1

        local_x2 = x2 - crop_x1

        local_y2 = y2 - crop_y1

        red = (0, 0, 255)

        cv2.rectangle(

            evidence,

            (local_x1, local_y1),

            (local_x2, local_y2),

            red,

            5,

        )

        center_x = int((local_x1 + local_x2) / 2)

        center_y = int((local_y1 + local_y2) / 2)

        radius_x = max(

            10,

            int((local_x2 - local_x1) / 2),

        )

        radius_y = max(

            10,

            int((local_y2 - local_y1) / 2),

        )

        cv2.ellipse(

            evidence,

            (center_x, center_y),

            (radius_x, radius_y),

            0,

            0,

            360,

            red,

            3,

        )
        label = (

            f"LOGO {candidate.candidate_id}"

        )

        font = cv2.FONT_HERSHEY_SIMPLEX

        font_scale = 0.65

        thickness = 2

        (text_width, text_height), baseline = cv2.getTextSize(

            label,

            font,

            font_scale,

            thickness,

        )

        label_x = max(

            5,

            local_x1,

        )

        label_y = max(

            text_height + 10,

            local_y1 - 10,

        )

    # Background behind label

        cv2.rectangle(

            evidence,

            (

                label_x - 5,

                label_y - text_height - 8,

            ),

            (
                label_x + text_width + 8,

                label_y + baseline + 4,

            ),

            (0, 0, 0),

            -1,

        )

        cv2.putText(

            evidence,

            label,

            (label_x, label_y),

            font,

            font_scale,

            red,

            thickness,

            cv2.LINE_AA,

        )
        max_dimension = 1400

        height, width = evidence.shape[:2]

        scale = min(

            1.0,

            max_dimension / max(height, width),

        )

        if scale < 1.0:

            evidence = cv2.resize(

                evidence,

                (

                    int(width * scale),

                    int(height * scale),

                ),

                interpolation=cv2.INTER_AREA,

            )

        output_path = Path(output_path)

        output_path.parent.mkdir(

            parents=True,

            exist_ok=True,

        )
        success = cv2.imwrite(

            str(output_path),

            evidence,

            [

                cv2.IMWRITE_PNG_COMPRESSION,

                3,

            ],

        )

        if not success:

            raise RuntimeError(

                f"Failed to write evidence image: {output_path}"

            )

        return str(output_path)