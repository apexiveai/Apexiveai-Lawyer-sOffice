import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from PIL import Image

from app.services.analysis_service import AnalysisService


class UploadedVisualAssetsTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.service = object.__new__(AnalysisService)
        self.service.job_id = "visual-upload-test"
        self.service.job_extracted_dir = self.root / "extracted"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_raster_image_is_loaded_and_saved_as_comparable_png(self):
        source = self.root / "trademark.png"
        Image.new("RGB", (24, 16), color="red").save(source)

        assets = self.service._extract_visual_assets(source, "left", "png")

        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]["width"], 24)
        self.assertEqual(assets[0]["height"], 16)
        self.assertTrue(Path(assets[0]["image_path"]).is_file())

    def test_svg_is_rendered_to_comparable_png(self):
        source = self.root / "trademark.svg"
        source.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="16">'
            '<rect width="24" height="16" fill="red"/></svg>',
            encoding="utf-8",
        )

        assets = self.service._extract_visual_assets(source, "right", "svg")

        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]["width"], 24)
        self.assertEqual(assets[0]["height"], 16)
        self.assertTrue(Path(assets[0]["image_path"]).is_file())

    def test_xlsx_and_pdf_are_routed_in_either_upload_order(self):
        xlsx_path = self.root / "left_document.xlsx"
        pdf_path = self.root / "right_document.pdf"
        self.service.left_path = xlsx_path
        self.service.right_path = pdf_path
        self.service.analysis_metadata = {}
        self.service.run = Mock(return_value={"job_id": "test"})

        result = self.service._run_uploaded_pair()

        self.assertEqual(result, {"job_id": "test"})
        self.assertEqual(self.service.pdf_path, pdf_path)
        self.assertEqual(self.service.xlsx_path, xlsx_path)

    def test_xlxs_extension_is_treated_as_xlsx(self):
        left_path = self.root / "left_document.xlxs"
        right_path = self.root / "right_document.xlsx"
        self.service.left_path = left_path
        self.service.right_path = right_path
        self.service._run_xlsx_pair = Mock(return_value={"job_id": "test"})

        result = self.service._run_uploaded_pair()

        self.assertEqual(result, {"job_id": "test"})
        self.assertEqual(self.service.left_xlsx_path, left_path)
        self.assertEqual(self.service.right_xlsx_path, right_path)


if __name__ == "__main__":
    unittest.main()
