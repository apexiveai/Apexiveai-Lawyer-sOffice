import tempfile
import unittest
from pathlib import Path

from app.services.analysis_service import AnalysisService


class AllLogoPairMatchesTests(unittest.TestCase):
    def test_returns_each_exact_logo_pair_instead_of_only_the_first(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            left_first = root / "left-first.png"
            right_first = root / "right-first.png"
            right_second = root / "right-second.png"

            left_first.write_bytes(b"same logo")
            right_first.write_bytes(b"same logo")
            right_second.write_bytes(b"same logo")

            left_logos = [
                {"image_path": str(left_first)},
            ]
            right_logos = [
                {"image_path": str(right_first)},
                {"image_path": str(right_second)},
            ]

            service = object.__new__(AnalysisService)
            matches = service._compare_logos(left_logos, right_logos)
            combined = service._combine_matches([], [], [], matches)

        actual_pairs = {
            (
                Path(match["pdf_logo"]["image_path"]).name,
                Path(match["client_logo"]["image_path"]).name,
            )
            for match in matches
        }

        self.assertEqual(
            actual_pairs,
            {
                ("left-first.png", "right-first.png"),
                ("left-first.png", "right-second.png"),
            },
        )
        self.assertEqual(len(combined), 2)
        self.assertTrue(all(match["logo_match"] for match in combined))
        self.assertTrue(
            all(match["decision"] == "EXACT_VISUAL_MATCH" for match in combined)
        )


if __name__ == "__main__":
    unittest.main()
