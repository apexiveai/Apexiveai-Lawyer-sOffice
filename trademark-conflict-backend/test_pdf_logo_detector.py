import json

import sys

from pathlib import Path

from app.services.pdf_logo_detector import (

    PDFLogoDetector,

)

def main():

    if len(sys.argv) < 2:

        print(

            "Usage:"

        )

        print(

            "python test_pdf_logo_detector.py "

            "\"C:\\path\\file.pdf\""

        )

        return

    pdf_path = Path(

        sys.argv[1]

    )

    if not pdf_path.exists():

        print(

            f"ERROR: PDF not found: "

            f"{pdf_path}"

        )

        return

    output_dir = (

        Path("extracted")

        / "pdf_detection_test"

    )

    detector = PDFLogoDetector(

        pdf_path=str(pdf_path),

        output_dir=str(output_dir),

        dpi=200,

    )

    result = detector.process()

    result_path = (

        output_dir

        / "detection_result.json"

    )

    result_path.write_text(

        json.dumps(

            result,

            indent=2,

            ensure_ascii=False,

        ),

        encoding="utf-8",

    )

    print()

    print("=" * 60)

    print("PDF LOGO DETECTION")

    print("=" * 60)

    print(

        f"PDF      : {result['pdf']}"

    )

    print(

        f"Pages    : {result['pages']}"

    )

    print(

        f"DPI      : {result['dpi']}"

    )

    print(

        f"Zoom     : {result['zoom']}"

    )

    print(

        f"Candidates: "

        f"{len(result['candidates'])}"

    )

    print()

    for candidate in result[

        "candidates"

    ]:

        bbox = candidate["bbox"]

        print(

            f"[{candidate['candidate_id']}]"

        )

        print(

            f"  Page       : "

            f"{candidate['page_number']}"

        )

        print(

            f"  Source     : "

            f"{candidate['source']}"

        )

        print(

            f"  Confidence : "

            f"{candidate['confidence']:.3f}"

        )

        print(

            f"  PDF BBox   : "

            f"x={bbox['pdf_x']:.2f}, "

            f"y={bbox['pdf_y']:.2f}, "

            f"w={bbox['pdf_width']:.2f}, "

            f"h={bbox['pdf_height']:.2f}"

        )

        print(

            f"  Pixel BBox : "

            f"x={bbox['x']}, "

            f"y={bbox['y']}, "

            f"w={bbox['width']}, "

            f"h={bbox['height']}"

        )

        print(

            f"  Crop       : "

            f"{candidate['crop_path']}"

        )

        print()

    print("=" * 60)

    print(

        f"JSON result:"

        f"\n{result_path}"

    )

if __name__ == "__main__":

    main()