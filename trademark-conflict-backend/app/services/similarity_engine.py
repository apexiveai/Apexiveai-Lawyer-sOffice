from pathlib import Path
from typing import Dict, List, Optional
import hashlib
from app.services.ai_logo.verifier import LogoAIVerifier
import cv2
import numpy as np


class SimilarityEngine:
    """
    Trademark visual similarity engine.

    Important design principle:
        A word-only mark such as "SunGold" should not receive
        a high logo similarity merely because its font or color
        resembles a complex figurative mark such as a logo
        containing people, fruits, objects, etc.

    The engine therefore separates:
        1. Word/appearance structure
        2. Foreground shape
        3. Edge structure
        4. Local visual features
        5. Color distribution

    Color/histogram is intentionally kept at a very low weight.
    """

    def __init__(self, threshold: float = 0.82):
        self.threshold = float(threshold)
        self.ai_verifier = LogoAIVerifier()
        self._digest_cache: Dict[str, str] = {}
        self._profile_cache: Dict[str, Dict] = {}
    # ============================================================
    # PUBLIC API
    # ============================================================

    def compare(
        self,
        image_a_path: str,
        image_b_path: str,
    ) -> Dict:

        # Identical source files or byte-identical extracted images are an
        # exact visual match by definition.
        # This also prevents interpolation/codec noise from lowering a
        # known same-image comparison below 100%.
        if (
            Path(image_a_path).resolve()
            == Path(image_b_path).resolve()
        ):
            return self._exact_match_result("Same source image")

        if self._file_digest(image_a_path) == self._file_digest(image_b_path):
            return self._exact_match_result("Byte-identical image")

        profile_a = self._get_profile(image_a_path, "A")
        profile_b = self._get_profile(image_b_path, "B")

        # --------------------------------------------------------
        # Compare visual components
        # --------------------------------------------------------

        shape_score = self._shape_similarity(
            profile_a["mask"],
            profile_b["mask"],
        )

        edge_score = self._edge_similarity(
            profile_a["edges"],
            profile_b["edges"],
        )

        structure_score = self._structural_similarity(
            profile_a["gray"],
            profile_b["gray"],
        )

        feature_score = self._feature_similarity(
            profile_a["gray"],
            profile_b["gray"],
        )

        hash_score = self._hash_similarity(
            profile_a["gray"],
            profile_b["gray"],
        )

        color_score = self._color_similarity(
            profile_a["image"],
            profile_b["image"],
        )

        # --------------------------------------------------------
        # Composition similarity
        #
        # A complex figurative mark should not match a simple
        # word-only mark merely because of text/font similarity.
        # --------------------------------------------------------

        composition_score = self._composition_similarity(
            profile_a,
            profile_b,
        )

        # --------------------------------------------------------
        # Base visual score
        # --------------------------------------------------------

        base_score = (
            shape_score * 0.30
            + edge_score * 0.20
            + structure_score * 0.15
            + feature_score * 0.15
            + hash_score * 0.10
            + color_score * 0.05
            + composition_score * 0.05
        )

        # --------------------------------------------------------
        # Figurative-vs-word-only penalty
        #
        # This is critical for cases like:
        #
        #   JELLY BUBBLE GUM
        #   + people + fruits
        #
        # versus:
        #
        #   SunGold
        #
        # If one mark contains substantial non-text imagery and
        # the other is essentially text-only, visual conflict
        # should not be declared from font similarity.
        # --------------------------------------------------------

        figurative_difference = abs(
            profile_a["figurative_ratio"]
            - profile_b["figurative_ratio"]
        )

        text_only_difference = (
            profile_a["text_likelihood"]
            - profile_b["text_likelihood"]
        )

        if (
        figurative_difference >= 0.35
            and abs(text_only_difference) >= 0.25
        ):
            base_score *= 0.65

        # --------------------------------------------------------
        # Strong shape disagreement
        # --------------------------------------------------------

        if shape_score < 0.35:
            base_score *= 0.80

        if edge_score < 0.10:
            base_score *= 0.85

        final_score = float(
            max(
                0.0,
                min(
                    1.0,
                    base_score,
                ),
            )
        )

        ai_result = self.ai_verifier.verify(

            {

                "similarity": final_score,

                "components": {

                    "shape": shape_score,

                    "edge": edge_score,

                    "structural": structure_score,

                    "feature": feature_score,

                    "hash": hash_score,

                    "color": color_score,

                    "composition": composition_score,

                },

            }

        )

        verified_score = ai_result.confidence

        status = ai_result.decision

        if final_score >= 0.90:
            status = "HIGH_SIMILARITY"

        elif final_score >= self.threshold:
            status = "SIMILAR"

        elif final_score >= 0.70:
            status = "REVIEW"

        else:
            status = "NO_MATCH"

        return {
            "similarity": verified_score,
            
            "similarity_percent": round(
                final_score * 100,
                2,
            ),
            "status": status,

            "ai_verification": {
                "verified": ai_result.verified,
                "confidence": round(
                    ai_result.confidence,
                    4,
                ),
                "confidence_percent": round(
                    ai_result.confidence * 100,
                    2,
                ),
                "decision": ai_result.decision,
                "reasons": ai_result.reasons,
            },

            "components": {
                "shape": round(
                    shape_score,
                    4,
                ),
                "edge": round(
                    edge_score,
                    4,
                ),
                "structural": round(
                    structure_score,
                    4,
                ),
                "feature": round(
                    feature_score,
                    4,
                ),
                "hash": round(
                    hash_score,
                    4,
                ),
                "color": round(
                    color_score,
                    4,
                ),
                "composition": round(
                    composition_score,
                    4,
                ),
            },

            "profiles": {
                "image_a": self._public_profile(
                    profile_a
                ),
                "image_b": self._public_profile(
                    profile_b
                ),
            },
        }

    def _file_digest(self, path: str) -> str:
        cache_key = self._cache_key(path)
        cached = self._digest_cache.get(cache_key)
        if cached is not None:
            return cached

        digest = hashlib.sha256()
        with Path(path).open("rb") as image_file:
            for chunk in iter(lambda: image_file.read(1024 * 1024), b""):
                digest.update(chunk)
        value = digest.hexdigest()
        self._digest_cache[cache_key] = value
        return value

    @staticmethod
    def _cache_key(path: str) -> str:
        image_path = Path(path).resolve()
        stat = image_path.stat()
        return f"{image_path}:{stat.st_size}:{stat.st_mtime_ns}"

    def _get_profile(self, path: str, label: str) -> Dict:
        cache_key = self._cache_key(path)
        cached = self._profile_cache.get(cache_key)
        if cached is not None:
            return cached

        image = self._load_image(path)
        if image is None:
            raise ValueError(f"Unable to read image {label}: {path}")

        profile = self._build_profile(image)
        self._profile_cache[cache_key] = profile
        return profile

    def _exact_match_result(self, reason: str) -> Dict:
        return {
            "similarity": 1.0,
            "similarity_percent": 100.0,
            "status": "EXACT",
            "ai_verification": {
                "verified": True,
                "confidence": 1.0,
                "confidence_percent": 100.0,
                "decision": "VERIFIED_MATCH",
                "reasons": [reason],
            },
            "components": {
                "shape": 1.0,
                "edge": 1.0,
                "structural": 1.0,
                "feature": 1.0,
                "hash": 1.0,
                "color": 1.0,
                "composition": 1.0,
            },
            "profiles": {},
        }

    # ============================================================
    # IMAGE LOADING
    # ============================================================

    @staticmethod
    def _load_image(
        image_path: str,
    ) -> Optional[np.ndarray]:

        path = Path(image_path)

        if not path.exists():
            return None

        image = cv2.imread(
            str(path),
            cv2.IMREAD_UNCHANGED,
        )

        if image is None:
            return None

        if len(image.shape) == 2:
            image = cv2.cvtColor(
                image,
                cv2.COLOR_GRAY2BGR,
            )

        elif (
            len(image.shape) == 3
            and image.shape[2] == 4
        ):
            alpha = image[:, :, 3]
            bgr = image[:, :, :3]

            background = np.full_like(
                bgr,
                255,
            )

            alpha_float = (
                alpha.astype(np.float32)
                / 255.0
            )

            alpha_float = alpha_float[
                :, :, None
            ]

            image = (
                bgr.astype(np.float32)
                * alpha_float
                + background.astype(np.float32)
                * (1.0 - alpha_float)
            ).astype(np.uint8)

        return image

    # ============================================================
    # PROFILE
    # ============================================================

    def _build_profile(
        self,
        image: np.ndarray,
    ) -> Dict:

        normalized = self._normalize_image(
            image
        )

        gray = cv2.cvtColor(
            normalized,
            cv2.COLOR_BGR2GRAY,
        )

        mask = self._foreground_mask(
            normalized
        )
        edges = cv2.Canny(
            gray,
            50,
            150,
        )

        foreground_ratio = (
            cv2.countNonZero(mask)
            / float(
                mask.shape[0]
                * mask.shape[1]
            )
        )

        contour_count = (
            self._count_contours(mask)
        )

        text_likelihood = (
            self._estimate_text_likelihood(
                gray,
                mask,
                contour_count,
            )
        )

        figurative_ratio = max(
            0.0,
            min(
                1.0,
                1.0 - text_likelihood,
            ),
        )

        return {
            "image": normalized,
            "gray": gray,
            "mask": mask,
            "edges": edges,
            "foreground_ratio": float(
                foreground_ratio
            ),
            "contour_count": int(
                contour_count
            ),
            "text_likelihood": float(
                text_likelihood
            ),
            "figurative_ratio": float(
                figurative_ratio
            ),
            "aspect_ratio": float(
                normalized.shape[1]
                / max(
                    normalized.shape[0],
                    1,
                )
            ),
        }

    @staticmethod
    def _public_profile(
        profile: Dict,
    ) -> Dict:

        return {
            "foreground_ratio": round(
                profile[
                    "foreground_ratio"
                ],
                4,
            ),
            "contour_count": profile[
                "contour_count"
            ],
            "text_likelihood": round(
                profile[
                    "text_likelihood"
                ],
                4,
            ),
            "figurative_ratio": round(
                profile[
                    "figurative_ratio"
                ],
                4,
            ),
            "aspect_ratio": round(
                profile[
                    "aspect_ratio"
                ],
                4,
            ),
        }

    # ============================================================
    # NORMALIZATION
    # ============================================================

    def _normalize_image(
        self,
        image: np.ndarray,
    ) -> np.ndarray:

        cropped = self._crop_content(
            image
        )

        if cropped is None:
            cropped = image

        return self._fit_to_canvas(
            cropped,
            size=256,
            padding=18,
        )

    # ============================================================
    # CONTENT CROP
    # ============================================================

    def _crop_content(
        self,
        image: np.ndarray,
    ) -> Optional[np.ndarray]:

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

        dark_mask = cv2.threshold(
            gray,
            245,
            255,
            cv2.THRESH_BINARY_INV,
        )[1]

        hsv = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2HSV,
        )

        saturation = hsv[:, :, 1]

        color_mask = cv2.threshold(
            saturation,
            25,
            255,
            cv2.THRESH_BINARY,
        )[1]

        mask = cv2.bitwise_or(
            dark_mask,
            color_mask,
        )

        kernel = np.ones(
            (3, 3),
            np.uint8,
        )

        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_CLOSE,
            kernel,
            iterations=2,
        )

        coords = cv2.findNonZero(
            mask
        )

        if coords is None:
            return image

        x, y, w, h = cv2.boundingRect(
            coords
        )

        image_h, image_w = image.shape[:2]

        ratio = (
            w * h
        ) / max(
            image_w * image_h,
            1,
        )

        if ratio < 0.01:
            return image

        if ratio > 0.98:
            return image

        margin_x = max(
            int(w * 0.05),
            3,
        )

        margin_y = max(
            int(h * 0.05),
            3,
        )

        x1 = max(
            0,
            x - margin_x,
        )

        y1 = max(
            0,
            y - margin_y,
        )

        x2 = min(
            image_w,
            x + w + margin_x,
        )

        y2 = min(
            image_h,
            y + h + margin_y,
        )

        return image[
            y1:y2,
            x1:x2,
        ]

    # ============================================================
    # CANVAS
    # ============================================================

    @staticmethod
    def _fit_to_canvas(
        image: np.ndarray,
        size: int = 256,
        padding: int = 18,
    ) -> np.ndarray:

        h, w = image.shape[:2]

        if h <= 0 or w <= 0:
            return np.full(
                (
                    size,
                    size,
                    3,
                ),
                255,
                dtype=np.uint8,
            )

        available = max(
            size - padding * 2,
            32,
        )

        scale = min(
            available / w,
            available / h,
        )

        new_w = max(
            1,
            int(round(w * scale)),
        )

        new_h = max(
            1,
            int(round(h * scale)),
        )

        interpolation = (
            cv2.INTER_AREA
            if scale < 1
            else cv2.INTER_CUBIC
        )

        resized = cv2.resize(
            image,
            (new_w, new_h),
            interpolation=interpolation,
        )

        canvas = np.full(
            (
                size,
                size,
                3,
            ),
            255,
            dtype=np.uint8,
        )

        x = (
            size - new_w
        ) // 2

        y = (
            size - new_h
        ) // 2

        canvas[
            y:y + new_h,
            x:x + new_w,
        ] = resized

        return canvas

    # ============================================================
    # FOREGROUND MASK
    # ============================================================

    @staticmethod
    def _foreground_mask(
        image: np.ndarray,
    ) -> np.ndarray:

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

        mask = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            31,
            8,
        )

        kernel = np.ones(
            (3, 3),
            np.uint8,
        )

        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_OPEN,
            kernel,
            iterations=1,
        )

        return mask

    # ============================================================
    # CONTOURS
    # ============================================================

    @staticmethod
    def _count_contours(
        mask: np.ndarray,
    ) -> int:

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        image_area = (
            mask.shape[0]
            * mask.shape[1]
        )

        valid = 0

        for contour in contours:

            area = cv2.contourArea(
                contour
            )

            if area >= image_area * 0.001:
                valid += 1

        return valid

    # ============================================================
    # TEXT LIKELIHOOD
    # ============================================================

    def _estimate_text_likelihood(
        self,
        gray: np.ndarray,
        mask: np.ndarray,
        contour_count: int,
    ) -> float:

        height, width = gray.shape

        # Horizontal morphology emphasizes text-like
        # connected components.
        horizontal_kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (
                max(
                    9,
                    width // 18,
                ),
                3,
            ),
        )

        horizontal = cv2.morphologyEx(
            mask,
            cv2.MORPH_OPEN,
            horizontal_kernel,
        )

        horizontal_pixels = (
            cv2.countNonZero(
                horizontal
            )
        )

        foreground_pixels = (
            cv2.countNonZero(
                mask
            )
        )

        if foreground_pixels == 0:
            return 0.0

        horizontal_ratio = (
            horizontal_pixels
            / foreground_pixels
        )

        # Text marks commonly have several small,
        # horizontally organized components.
        contour_signal = min(
            contour_count / 12.0,
            1.0,
        )

        score = (
            horizontal_ratio * 0.65
            + contour_signal * 0.35
        )

        return float(
            max(
                0.0,
                min(
                    1.0,
                    score,
                )
            )
        )

    # ============================================================
    # SHAPE
    # ============================================================

    @staticmethod
    def _shape_similarity(
        mask_a: np.ndarray,
        mask_b: np.ndarray,
    ) -> float:

        a = cv2.resize(
            mask_a,
            (256, 256),
            interpolation=cv2.INTER_NEAREST,
        )

        b = cv2.resize(
            mask_b,
            (256, 256),
            interpolation=cv2.INTER_NEAREST,
        )

        intersection = cv2.bitwise_and(
            a,
            b,
        )

        union = cv2.bitwise_or(
            a,
            b,
        )

        intersection_area = (
            cv2.countNonZero(
                intersection
            )
        )

        union_area = (
            cv2.countNonZero(
                union
            )
        )

        if union_area == 0:
            return 0.0

        return float(
            intersection_area
            / union_area
        )

    # ============================================================
    # EDGE
    # ============================================================

    @staticmethod
    def _edge_similarity(
        edges_a: np.ndarray,
        edges_b: np.ndarray,
    ) -> float:

        a = cv2.resize(
            edges_a,
            (256, 256),
            interpolation=cv2.INTER_NEAREST,
        )

        b = cv2.resize(
            edges_b,
            (256, 256),
            interpolation=cv2.INTER_NEAREST,
        )

        intersection = cv2.bitwise_and(
            a,
            b,
        )

        union = cv2.bitwise_or(
            a,
            b,
        )

        union_count = cv2.countNonZero(
            union
        )

        if union_count == 0:
            return 0.0

        return float(
            cv2.countNonZero(
                intersection
            )
            / union_count
        )

    # ============================================================
    # STRUCTURAL
    # ============================================================

    @staticmethod
    def _structural_similarity(
        gray_a: np.ndarray,
        gray_b: np.ndarray,
    ) -> float:

        a = cv2.resize(
            gray_a,
            (256, 256),
            interpolation=cv2.INTER_AREA,
        ).astype(np.float32)

        b = cv2.resize(
            gray_b,
            (256, 256),
            interpolation=cv2.INTER_AREA,
        ).astype(np.float32)

        mean_a = float(
            a.mean()
        )

        mean_b = float(
            b.mean()
        )

        variance_a = float(
            a.var()
        )

        variance_b = float(
            b.var()
        )

        covariance = float(
            np.mean(
                (a - mean_a)
                * (b - mean_b)
            )
        )

        c1 = 6.5025
        c2 = 58.5225

        numerator = (
            (2 * mean_a * mean_b + c1)
            * (2 * covariance + c2)
)

        denominator = (
            (
                mean_a ** 2
                + mean_b ** 2
                + c1
            )
            * (
                variance_a
                + variance_b
                + c2
            )
        )

        if denominator == 0:
            return 0.0

        score = (
            numerator
            / denominator
        )

        return float(
            max(
                0.0,
                min(
                    1.0,
                    score,
                )
            )
        )

    # ============================================================
    # FEATURE
    # ============================================================

    @staticmethod
    def _feature_similarity(
        gray_a: np.ndarray,
        gray_b: np.ndarray,
    ) -> float:

        orb = cv2.ORB_create(
            nfeatures=1500,
            scaleFactor=1.2,
            nlevels=8,
            edgeThreshold=15,
            patchSize=31,
            fastThreshold=10,
        )

        keypoints_a, descriptors_a = (
            orb.detectAndCompute(
                gray_a,
                None,
            )
        )

        keypoints_b, descriptors_b = (
            orb.detectAndCompute(
                gray_b,
                None,
            )
        )

        if (
            descriptors_a is None
            or descriptors_b is None
        ):
            return 0.0

        if (
            len(descriptors_a) < 2
            or len(descriptors_b) < 2
        ):
            return 0.0

        matcher = cv2.BFMatcher(
            cv2.NORM_HAMMING,
            crossCheck=False,
        )

        try:
            matches = matcher.knnMatch(
                descriptors_a,
                descriptors_b,
                k=2,
            )
        except Exception:
            return 0.0

        good = []

        for pair in matches:

            if len(pair) != 2:
                continue

            first, second = pair

            if (
                first.distance
                < 0.78 * second.distance
            ):
                good.append(
                    first
                )

        denominator = max(
            min(
                len(keypoints_a),
                len(keypoints_b),
            ),
            1,
        )

        return float(
            max(
                0.0,
                min(
                    1.0,
                    len(good)
                    / denominator,
                )
            )
        )

    # ============================================================
    # HASH
    # ============================================================

    @staticmethod
    def _hash_similarity(
        gray_a: np.ndarray,
        gray_b: np.ndarray,
    ) -> float:

        def dhash(
            gray: np.ndarray,
        ) -> np.ndarray:

            resized = cv2.resize(
                gray,
                (17, 16),
                interpolation=cv2.INTER_AREA,
            )

            return (
                resized[:, 1:]
                > resized[:, :-1]
            ).flatten()

        hash_a = dhash(
            gray_a
        )

        hash_b = dhash(
            gray_b
        )

        if hash_a.size == 0:
            return 0.0

        distance = np.count_nonzero(
            hash_a != hash_b
        )

        return float(
            1.0
            - (
                distance
                / hash_a.size
            )
        )

    # ============================================================
    # COLOR
    # ============================================================

    @staticmethod
    def _color_similarity(
        image_a: np.ndarray,
        image_b: np.ndarray,
    ) -> float:

        hsv_a = cv2.cvtColor(
            image_a,
            cv2.COLOR_BGR2HSV,
        )

        hsv_b = cv2.cvtColor(
            image_b,
            cv2.COLOR_BGR2HSV,
        )

        hist_a = cv2.calcHist(
            [hsv_a],
            [0, 1],
            None,
            [32, 32],
            [0, 180, 0, 256],
        )

        hist_b = cv2.calcHist(
            [hsv_b],
            [0, 1],
            None,
            [32, 32],
            [0, 180, 0, 256],
        )

        cv2.normalize(
            hist_a,
            hist_a,
            0,
            1,
            cv2.NORM_MINMAX,
        )

        cv2.normalize(
            hist_b,
            hist_b,
            0,
            1,
            cv2.NORM_MINMAX,
        )

        correlation = cv2.compareHist(
            hist_a,
            hist_b,
            cv2.HISTCMP_CORREL,
        )

        return float(
            max(
                0.0,
                min(
                    1.0,
                    correlation,
                )
            )
        )

    # ============================================================
    # COMPOSITION
    # ============================================================

    @staticmethod
    def _composition_similarity(
        profile_a: Dict,
        profile_b: Dict,
    ) -> float:

        contour_a = min(
            profile_a[
                "contour_count"
            ] / 20.0,
            1.0,
        )

        contour_b = min(
            profile_b[
                "contour_count"
            ] / 20.0,
            1.0,
        )

        foreground_a = profile_a[
            "foreground_ratio"
        ]

        foreground_b = profile_b[
            "foreground_ratio"
        ]

        contour_similarity = (
            1.0
            - abs(
                contour_a
                - contour_b
            )
        )

        foreground_similarity = (
            1.0
            - min(
                abs(
                    foreground_a
                    - foreground_b
                ),
                1.0,
            )
        )

        aspect_similarity = (
            1.0
            - min(
                abs(
                    profile_a[
                        "aspect_ratio"
                    ]
                    - profile_b[
                        "aspect_ratio"
                    ]
                )
                / 3.0,
                1.0,
            )
        )

        return float(
            max(
                0.0,
                min(
                    1.0,
                    (
                        contour_similarity
                        * 0.45
                        + foreground_similarity
                        * 0.30
                        + aspect_similarity
                        * 0.25
                    ),
                ),
            )
        )

    # ============================================================
    # FIND MATCHES
    # ============================================================

    def find_matches(
        self,
        original_logos: List[Dict],
        compare_logos: List[Dict],
    ) -> List[Dict]:

        results = []

        for original in original_logos:

            best_match = None

            for compare in compare_logos:

                try:

                    result = self.compare(
                        original[
                            "image_path"
                        ],
                        compare[
                            "image_path"
                        ],
                    )

                except Exception:
                    continue

                candidate = {
                    "original": original,
                    "compare": compare,
                    **result,
                }

                if (
                    best_match is None
                    or result[
                        "similarity"
                    ]
                    > best_match[
                        "similarity"
                    ]
                ):
                    best_match = candidate

            if best_match is None:
                continue

            if (
                best_match[
                    "similarity"
                ]
                >= self.threshold
            ):
                results.append(
                    best_match
                )

        results.sort(
            key=lambda item:
                item["similarity"],
            reverse=True,
        )

        return results