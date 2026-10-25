from pathlib import Path

from typing import Optional

import cv2

import numpy as np

from app.core.config import EVIDENCE_DIR

class EvidenceRenderer:

    def __init__(self, job_id: str):

        self.job_id = job_id

        self.output_dir = (

            EVIDENCE_DIR /

            job_id

        )

        self.output_dir.mkdir(

            parents=True,

            exist_ok=True,

        )

    def render_logo(

        self,

        image_path: str,

        output_name: str,

        label: str,

        bbox: Optional[tuple] = None,

    ) -> str:

        image = cv2.imread(

            image_path,

            cv2.IMREAD_COLOR,

        )

        if image is None:

            raise ValueError(

                f"Cannot read image: {image_path}"

            )

        height, width = image.shape[:2]

        if bbox is None:

            # For extracted standalone logos,

            # use the complete image area.

            margin_x = max(

                int(width * 0.06),

                5,

            )

            margin_y = max(

                int(height * 0.06),

                5,

            )

            x1 = margin_x

            y1 = margin_y

            x2 = width - margin_x

            y2 = height - margin_y

        else:

            x, y, w, h = bbox

            padding_x = int(w * 0.12)

            padding_y = int(h * 0.12)

            x1 = max(

                0,

                x - padding_x,

            )

            y1 = max(

                0,

                y - padding_y,

            )

            x2 = min(

                width - 1,

                x + w + padding_x,

            )

            y2 = min(

                height - 1,

                y + h + padding_y,

            )

        center = (

            (x1 + x2) // 2,

            (y1 + y2) // 2,

        )

        axes = (

            max(

                (x2 - x1) // 2,

                10,

            ),

            max(

                (y2 - y1) // 2,

                10,

            ),

        )

        # Main ellipse

        cv2.ellipse(

            image,

            center,

            axes,

            0,

            0,

            360,

            (0, 0, 255),

            5,

            cv2.LINE_AA,

        )

        # Inner ellipse for visibility

        inner_axes = (

            max(

                axes[0] - 8,

                5,

            ),

            max(

                axes[1] - 8,

                5,

            ),

        )

        cv2.ellipse(

            image,

            center,

            inner_axes,

            0,

            0,

            360,

            (0, 0, 255),

            2,

            cv2.LINE_AA,

        )

        # Label background

        font = cv2.FONT_HERSHEY_SIMPLEX

        font_scale = 0.8

        thickness = 2

        text_size = cv2.getTextSize(

            label,

            font,

            font_scale,

            thickness,

        )[0]

        text_x = max(

            10,

            x1,

        )

        text_y = max(

            text_size[1] + 15,

            y1 - 10,

        )

        cv2.rectangle(

            image,

            (

                text_x - 5,

                text_y - text_size[1] - 10,

            ),

            (

                text_x + text_size[0] + 5,

                text_y + 5,

            ),

            (0, 0, 255),

            -1,

        )

        cv2.putText(

            image,

            label,

            (

                text_x,

                text_y,

            ),

            font,

            font_scale,

            (255, 255, 255),

            thickness,

            cv2.LINE_AA,

        )

        output_path = (

            self.output_dir /

            output_name

        )

        success = cv2.imwrite(

            str(output_path),

            image,

        )

        if not success:

            raise IOError(

                f"Failed to write evidence: "

                f"{output_path}"
                )

        return str(output_path)