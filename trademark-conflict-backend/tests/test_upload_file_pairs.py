import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from app.api.upload import _validate_upload_pair


def upload(filename: str) -> SimpleNamespace:
    return SimpleNamespace(filename=filename)


class UploadFilePairTests(unittest.TestCase):
    def test_accepts_pdf_and_xlsx(self):
        _validate_upload_pair(
            pdf=upload("journal.pdf"),
            xlsx=upload("portfolio.xlsx"),
            client_pdf=None,
            left_xlsx=None,
            right_xlsx=None,
        )

    def test_accepts_two_pdfs(self):
        _validate_upload_pair(
            pdf=upload("first.pdf"),
            xlsx=None,
            client_pdf=upload("second.pdf"),
            left_xlsx=None,
            right_xlsx=None,
        )

    def test_accepts_two_xlsx_files(self):
        _validate_upload_pair(
            pdf=None,
            xlsx=None,
            client_pdf=None,
            left_xlsx=upload("first.xlsx"),
            right_xlsx=upload("second.xlsx"),
        )

    def test_rejects_incomplete_or_mixed_xlsx_pair_fields(self):
        with self.assertRaises(HTTPException) as incomplete:
            _validate_upload_pair(
                pdf=None,
                xlsx=None,
                client_pdf=None,
                left_xlsx=upload("first.xlsx"),
                right_xlsx=None,
            )
        self.assertEqual(incomplete.exception.status_code, 400)

        with self.assertRaises(HTTPException) as mixed:
            _validate_upload_pair(
                pdf=upload("first.pdf"),
                xlsx=None,
                client_pdf=None,
                left_xlsx=upload("second.xlsx"),
                right_xlsx=upload("third.xlsx"),
            )
        self.assertEqual(mixed.exception.status_code, 400)

    def test_rejects_unsupported_extensions_and_missing_files(self):
        with self.assertRaises(HTTPException):
            _validate_upload_pair(
                pdf=upload("first.pdf"),
                xlsx=upload("second.xls"),
                client_pdf=None,
                left_xlsx=None,
                right_xlsx=None,
            )

        with self.assertRaises(HTTPException):
            _validate_upload_pair(
                pdf=None,
                xlsx=upload("portfolio.xlsx"),
                client_pdf=None,
                left_xlsx=None,
                right_xlsx=None,
            )


if __name__ == "__main__":
    unittest.main()
