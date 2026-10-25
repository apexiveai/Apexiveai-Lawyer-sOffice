from __future__ import annotations

from pathlib import Path

from typing import Optional

import cv2

import numpy as np

class LogoDetector:

    def __init__(

        self,

        min_width: int = 40,

        min_height: int = 40,

        max_page_ratio: float = 0.20,

    ):

        self.min_width = min_width

        self.min_height = min_height

        self.max_page_ratio = max_page_ratio

    # =========================================================

    # MAIN

    # =========================================================

    def analyze_candidate(

        self,

        image,

        bbox,

    ) -> dict:

        x, y, w, h = bbox

        page_height, page_width = (

            image.shape[:2]

        )

        crop = self._safe_crop(

            image,

            bbox,

        )

        if crop is None:

            return {

                "is_logo": False,

                "score": 0.0,

                "reasons": [

                    "invalid_crop"

                ],

            }

        features = self.extract_features(

            crop,

            bbox,

            page_width,

            page_height,

        )

        score = 0.0

        reasons = []

        # -----------------------------------------------------

        # Size

        # -----------------------------------------------------

        if (

            w >= self.min_width

            and h >= self.min_height

        ):

            score += 0.10

            reasons.append("valid_size")

        # -----------------------------------------------------

        # Aspect ratio

        # -----------------------------------------------------

        aspect = features[

            "aspect_ratio"

        ]

        if aspect <= 4.5:

            score += 0.15

            reasons.append(

                "reasonable_aspect_ratio"

            )

        if aspect <= 2.5:

            score += 0.10

        # -----------------------------------------------------

        # Area

        # -----------------------------------------------------

        area_ratio = features[

            "area_ratio"

        ]

        if (

            0.0003

            <= area_ratio

            <= self.max_page_ratio

        ):

            score += 0.15

            reasons.append(

                "reasonable_area"

            )

        # -----------------------------------------------------

        # Edge density

        # -----------------------------------------------------

        edge_density = features[

            "edge_density"

        ]

        if 0.02 <= edge_density <= 0.45:

            score += 0.15

            reasons.append(

                "reasonable_edge_density"

            )

        # -----------------------------------------------------

        # Color diversity

        # -----------------------------------------------------

        color_score = features[

            "color_diversity"

        ]

        if color_score >= 0.15:

            score += 0.10

            reasons.append(

                "color_information"

            )

        # -----------------------------------------------------

        # Shape complexity

        # -----------------------------------------------------

        contour_score = features[

            "contour_complexity"

        ]

        if contour_score >= 0.15:

            score += 0.10

            reasons.append(

                "shape_complexity"

            )

        # -----------------------------------------------------

        # Foreground ratio

        # -----------------------------------------------------

        foreground = features[

            "foreground_ratio"

        ]

        if 0.03 <= foreground <= 0.85:

            score += 0.10

            reasons.append(

                "reasonable_foreground"

            )

        # -----------------------------------------------------

        # Border detection

        # -----------------------------------------------------

        border_score = features[
"border_likelihood"

        ]

        if border_score < 0.75:

            score += 0.10

            reasons.append(

                "not_simple_border"

            )

        else:

            score -= 0.20

            reasons.append(

                "possible_table_or_border"

            )

        score = max(

            0.0,

            min(1.0, score),

        )

        is_logo = score >= 0.50

        return {

            "is_logo": is_logo,

            "score": round(score, 4),

            "reasons": reasons,

            "features": features,

        }

    # =========================================================

    # FEATURES

    # =========================================================

    def extract_features(

        self,

        crop,

        bbox,

        page_width,

        page_height,

    ) -> dict:

        x, y, w, h = bbox

        gray = cv2.cvtColor(

            crop,

            cv2.COLOR_BGR2GRAY,

        )

        hsv = cv2.cvtColor(

            crop,

            cv2.COLOR_BGR2HSV,

        )

        # -----------------------------------------------------

        # Aspect

        # -----------------------------------------------------

        aspect_ratio = (

            max(w, h)

            / max(min(w, h), 1)

        )

        # -----------------------------------------------------

        # Area

        # -----------------------------------------------------

        area_ratio = (

            (w * h)

            / max(

                page_width * page_height,

                1,

            )

        )

        # -----------------------------------------------------

        # Edge density

        # -----------------------------------------------------

        edges = cv2.Canny(

            gray,

            50,

            150,

        )

        edge_density = (

            np.count_nonzero(edges)

            / max(edges.size, 1)

        )

        # -----------------------------------------------------

        # Color diversity

        # -----------------------------------------------------

        hsv_pixels = hsv.reshape(

            -1,

            3,

        )

        saturation = hsv_pixels[:, 1]

        color_diversity = (

            np.count_nonzero(

                saturation > 35

            )

            / max(

                len(saturation),

                1,

            )

        )

        # -----------------------------------------------------

        # Threshold foreground

        # -----------------------------------------------------

        _, binary = cv2.threshold(

            gray,

            0,

            255,

            cv2.THRESH_BINARY_INV

            + cv2.THRESH_OTSU,

        )

        foreground_ratio = (

            np.count_nonzero(binary)

            / max(

                binary.size,

                1,

            )

        )

        # -----------------------------------------------------

        # Contour complexity

        # -----------------------------------------------------

        contours, _ = cv2.findContours(

            binary,

            cv2.RETR_EXTERNAL,

            cv2.CHAIN_APPROX_SIMPLE,

        )

        contour_count = len(

            contours

        )

        contour_complexity = min(

            contour_count / 15.0,

            1.0,

        )

        # -----------------------------------------------------

        # Border likelihood

        # -----------------------------------------------------

        border_likelihood = (

            self._border_likelihood(

                edges

            )

        )

        return {

            "width": w,

            "height": h,

            "aspect_ratio": round(

                aspect_ratio,

                4,

            ),

            "area_ratio": round(

                area_ratio,

                6,

            ),

            "edge_density": round(

                float(edge_density),

                6,

            ),
            "color_diversity": round(

                float(color_diversity),

                6,

            ),

            "foreground_ratio": round(

                float(foreground_ratio),

                6,

            ),

            "contour_count": contour_count,

            "contour_complexity": round(

                float(contour_complexity),

                6,

            ),

            "border_likelihood": round(

                float(border_likelihood),

                6,

            ),

        }

    # =========================================================

    # BORDER

    # =========================================================

    @staticmethod

    def _border_likelihood(

        edges,

    ) -> float:

        height, width = (

            edges.shape[:2]

        )

        band = max(

            3,

            int(

                min(

                    height,

                    width,

                )

                * 0.05

            ),

        )

        top = edges[

            :band,

            :,

        ]

        bottom = edges[

            height - band:,

            :,

        ]

        left = edges[

            :,

            :band,

        ]

        right = edges[

            :,

            width - band:,

        ]

        border_pixels = np.concatenate(

            [

                top.flatten(),

                bottom.flatten(),

                left.flatten(),

                right.flatten(),

            ]

        )

        density = (

            np.count_nonzero(

                border_pixels

            )

            / max(

                len(border_pixels),

                1,

            )

        )

        return float(

            min(density * 3.0, 1.0)

        )

    # =========================================================

    # CROP

    # =========================================================

    @staticmethod

    def _safe_crop(

        image,

        bbox,

    ):

        x, y, w, h = bbox

        height, width = (

            image.shape[:2]

        )

        x1 = max(

            0,

            x,

        )

        y1 = max(

            0,

            y,

        )

        x2 = min(

            width,

            x + w,

        )

        y2 = min(

            height,

            y + h,

        )

        if x2 <= x1 or y2 <= y1:

            return None

        crop = image[

            y1:y2,

            x1:x2,

        ]

        if crop.size == 0:

            return None

        return crop