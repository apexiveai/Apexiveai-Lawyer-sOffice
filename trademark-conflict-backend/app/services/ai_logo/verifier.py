from __future__ import annotations

from dataclasses import dataclass

from typing import Dict

@dataclass

class AIVerificationResult:

    verified: bool

    confidence: float

    decision: str

    reasons: list[str]

class LogoAIVerifier:

    """

    Verification layer for trademark logo conflicts.

    This layer does NOT replace the existing OpenCV similarity engine.

    It validates whether a high visual score is supported by multiple

    independent visual signals.

    """

    def __init__(

        self,

        high_threshold: float = 0.90,

        review_threshold: float = 0.82,

    ) -> None:

        self.high_threshold = high_threshold

        self.review_threshold = review_threshold

    def verify(

        self,

        comparison: Dict,

    ) -> AIVerificationResult:

        similarity = float(

            comparison.get("similarity", 0.0)

        )

        components = comparison.get(

            "components",

            {},

        )

        shape = float(

            components.get("shape", 0.0)

        )

        edge = float(

            components.get("edge", 0.0)

        )

        structural = float(

            components.get("structural", 0.0)

        )

        feature = float(

            components.get("feature", 0.0)

        )

        hash_score = float(

            components.get("hash", 0.0)

        )

        composition = float(

            components.get("composition", 0.0)

        )

        reasons: list[str] = []

        # --------------------------------------------------

        # Independent visual agreement

        # --------------------------------------------------

        strong_shape = shape >= 0.65

        strong_structure = structural >= 0.65

        strong_feature = feature >= 0.50

        strong_composition = composition >= 0.65

        strong_edge = edge >= 0.20

        strong_hash = hash_score >= 0.70

        independent_signals = sum(

            [

                strong_shape,

                strong_structure,

                strong_feature,

                strong_composition,

                strong_edge,

                strong_hash,

            ]

        )

        # --------------------------------------------------

        # Evidence reasons

        # --------------------------------------------------

        if strong_shape:

            reasons.append(

                "Strong geometric/shape agreement"

            )

        if strong_structure:

            reasons.append(

                "Strong structural agreement"

            )

        if strong_feature:

            reasons.append(

                "Local visual feature agreement"

            )

        if strong_composition:

            reasons.append(

                "Composition agreement"

            )

        if strong_edge:

            reasons.append(

                "Edge pattern agreement"

            )

        if strong_hash:

            reasons.append(

                "Image-level similarity agreement"

            )

        # --------------------------------------------------

        # Verification confidence

        #

        # Similarity alone is never sufficient.

        # Multiple independent signals must agree.

        # --------------------------------------------------

        confidence = similarity

        if independent_signals >= 5:

            confidence += 0.05

        elif independent_signals >= 4:

            confidence += 0.025

        elif independent_signals <= 2:

            confidence -= 0.10

        # Strong shape disagreement is important.

        if shape < 0.35:

            confidence -= 0.10

            reasons.append(

                "Weak shape agreement"

            )

        if edge < 0.10:

            confidence -= 0.05

            reasons.append(

                "Weak edge agreement"

            )

        confidence = max(

            0.0,

            min(

                1.0,

                confidence,

            ),

        )
# --------------------------------------------------

        # Final decision

        # --------------------------------------------------

        if (

            confidence >= self.high_threshold

            and independent_signals >= 4

        ):

            decision = "VERIFIED_MATCH"

            verified = True

        elif (

            confidence >= self.review_threshold

            and independent_signals >= 3

        ):

            decision = "REVIEW"

            verified = False

        else:

            decision = "NO_MATCH"

            verified = False

        return AIVerificationResult(

            verified=verified,

            confidence=confidence,

            decision=decision,

            reasons=reasons,

        )