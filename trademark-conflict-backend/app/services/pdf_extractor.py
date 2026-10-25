from pathlib import Path

from typing import List, Dict

import pymupdf

import cv2

import numpy as np

from app.core.config import EXTRACTED_DIR

class PDFExtractor:

    def __init__(self, pdf_path: str):

        self.pdf_path = Path(pdf_path)

    def get_page_count(self) -> int:

        with pymupdf.open(self.pdf_path) as document:

            return len(document)

    def extract_images(

        self,

        job_id: str,

    ) -> List[Dict]:

        output_dir = (

            EXTRACTED_DIR /

            job_id /

            "pdf"

        )

        output_dir.mkdir(

            parents=True,

            exist_ok=True,

        )

        results = []

        with pymupdf.open(self.pdf_path) as document:

            for page_index, page in enumerate(

                document,

                start=1,

            ):

                images = page.get_images(

                    full=True

                )

                for image_index, image_info in enumerate(

                    images,

                    start=1,

                ):

                    xref = image_info[0]

                    try:

                        base_image = document.extract_image(

                            xref

                        )

                    except Exception:

                        continue

                    image_bytes = base_image["image"]

                    extension = base_image["ext"]

                    filename = (

                        f"page_{page_index:04d}"

                        f"_image_{image_index:04d}"

                        f".{extension}"

                    )

                    image_path = (

                        output_dir / filename

                    )

                    image_path.write_bytes(

                        image_bytes

                    )

                    image = cv2.imread(

                        str(image_path),

                        cv2.IMREAD_COLOR,

                    )

                    if image is None:

                        continue

                    height, width = image.shape[:2]

                    results.append({

                        "id": (

                            f"pdf_"

                            f"{page_index}_"

                            f"{image_index}"

                        ),

                        "source_type": "pdf",

                        "source_file": self.pdf_path.name,

                        "page": page_index,

                        "sheet": None,

                        "cell": None,

                        "image_path": str(

                            image_path

                        ),

                        "bbox": None,

                        "width": width,

                        "height": height,

                        "confidence": 1.0,

                    })

        return results

    def render_pages(

        self,

        job_id: str,

        dpi: int = 150,

    ) -> List[Dict]:

        output_dir = (

            EXTRACTED_DIR /

            job_id /

            "pdf_pages"

        )

        output_dir.mkdir(

            parents=True,

            exist_ok=True,

        )

        results = []

        zoom = dpi / 72.0

        matrix = pymupdf.Matrix(

            zoom,

            zoom,

        )

        with pymupdf.open(self.pdf_path) as document:

            for page_index, page in enumerate(

                document,

                start=1,

            ):

                pixmap = page.get_pixmap(

                    matrix=matrix,

                    alpha=False,

                )

                filename = (

                    f"page_{page_index:04d}.png"

                )

                output_path = (

                    output_dir / filename

                )

                pixmap.save(

                    str(output_path)

                )

                results.append({

                    "page": page_index,

                    "image_path": str(

                        output_path
),

                    "width": pixmap.width,

                    "height": pixmap.height,

                })

        return results