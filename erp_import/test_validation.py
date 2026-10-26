"""Lab 2 – tests for the ERP file validation, ImportLog and file moving (owner: Ami).

Run: python manage.py test erp_import
They use the sample files in erp_exchange/samples/ (the first one is a real ERP export).
"""
import shutil
import tempfile
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.test import TestCase, override_settings

from .files import FAILED, PROCESSED, exchange_folder, inbox_files, move_file
from .models import ImportLog
from .validation import InvalidFileError, read_and_validate

SAMPLES = Path(settings.BASE_DIR) / "erp_exchange" / "samples"


class ValidFileTests(TestCase):
    def test_real_erp_export(self):
        rows, errors = read_and_validate(SAMPLES / "valid_erp_export.xlsx")
        self.assertEqual(errors, [])
        by_id = {row["erp_id"]: row for row in rows}
        self.assertEqual(set(by_id), {"BOOK1002", "BOOK1001"})
        self.assertEqual(by_id["BOOK1001"], {"erp_id": "BOOK1001", "name": "1984", "description": "",
                                             "price": Decimal("9.99"), "stock": 25})

    def test_csv_with_semicolon_and_decimal_comma(self):
        rows, errors = read_and_validate(SAMPLES / "valid_export.csv")
        self.assertEqual(errors, [])
        self.assertEqual([row["price"] for row in rows], [Decimal("9.99"), Decimal("12.99")])

    def test_updated_export(self):
        rows, errors = read_and_validate(SAMPLES / "updated_erp_export.xlsx")
        self.assertEqual(errors, [])
        by_id = {row["erp_id"]: row for row in rows}
        self.assertEqual(by_id["BOOK1002"]["stock"], 0)
        self.assertEqual(by_id["BOOK1001"]["price"], Decimal("8.99"))
        self.assertIn("BOOK2001", by_id)


class RowErrorTests(TestCase):
    """Bad rows are skipped, good rows are kept."""

    def setUp(self):
        self.rows, self.errors = read_and_validate(SAMPLES / "export_with_errors.xlsx")
        self.text = "\n".join(self.errors)

    def test_good_rows_are_kept(self):
        self.assertEqual([row["erp_id"] for row in self.rows], ["BOOK1001", "BOOK2002"])
        self.assertEqual(self.rows[1]["price"], Decimal("7.90"))  # "7,90"

    def test_every_bad_row_is_reported(self):
        self.assertEqual(len(self.errors), 7)
        self.assertIn("Row 3: Price 'abc' is not a number", self.text)
        self.assertIn("Row 4: Price -5 is negative", self.text)
        self.assertIn("Row 5: Stock '2.5' is not a whole number", self.text)
        self.assertIn("Row 6: Stock -1 is negative", self.text)
        self.assertIn("Row 7: Product ID is missing", self.text)
        self.assertIn("Row 8: Product Name is missing", self.text)
        self.assertIn("Row 9: Product ID 'BOOK1001' appears more than once", self.text)


class FileErrorTests(TestCase):
    """The whole file is rejected."""

    def assert_rejected(self, file_name, message):
        with self.assertRaises(InvalidFileError) as caught:
            read_and_validate(SAMPLES / file_name)
        self.assertIn(message, str(caught.exception))

    def test_wrong_file_type(self):
        self.assert_rejected("wrong_format.txt", "Wrong file type")

    def test_not_really_excel(self):
        self.assert_rejected("not_really_excel.xlsx", "can't be opened as an Excel file")

    def test_missing_columns(self):
        self.assert_rejected("missing_columns.xlsx", "Required column(s) missing: Stock")

    def test_no_products(self):
        self.assert_rejected("empty_export.xlsx", "no products")

    def test_missing_file(self):
        self.assert_rejected("does_not_exist.xlsx", "File not found")


class ImportLogTests(TestCase):
    def test_status(self):
        self.assertEqual(ImportLog.record("a.xlsx", created=2).status, ImportLog.Status.SUCCESS)
        partial = ImportLog.record("b.xlsx", created=1, errors=["Row 3: Price 'abc' is not a number",
                                                                "Row 3: Stock -1 is negative",
                                                                "Row 5: Product ID is missing"])
        self.assertEqual(partial.status, ImportLog.Status.PARTIAL)
        self.assertEqual(partial.failed_count, 2)  # row 3 counted once
        self.assertEqual(ImportLog.record("c.xlsx", errors=["Row 2: Product ID is missing"]).status,
                         ImportLog.Status.FAILED)
        rejected = ImportLog.record("d.txt", file_error="Wrong file type '.txt'.")
        self.assertEqual((rejected.status, rejected.errors), (ImportLog.Status.FAILED, ["Wrong file type '.txt'."]))

    def test_admin_shows_log_read_only(self):
        from django.contrib.auth.models import User
        ImportLog.record("export.xlsx", created=1, errors=["Row 3: Price 'abc' is not a number"])
        User.objects.create_superuser("boss", "", "pw")
        self.client.login(username="boss", password="pw")
        response = self.client.get("/admin/erp_import/importlog/")
        self.assertContains(response, "export.xlsx")
        log = ImportLog.objects.get()
        self.assertContains(self.client.get(f"/admin/erp_import/importlog/{log.pk}/change/"),
                            "Price &#x27;abc&#x27; is not a number")
        self.assertEqual(self.client.get("/admin/erp_import/importlog/add/").status_code, 403)


class FileMoveTests(TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.override = override_settings(ERP_EXCHANGE_DIR=self.tmp)
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.tmp)

    def test_inbox_and_move(self):
        inbox = exchange_folder("inbox")
        shutil.copy(SAMPLES / "valid_erp_export.xlsx", inbox / "Products.xlsx")
        (inbox / ".gitkeep").touch()
        self.assertEqual([path.name for path in inbox_files()], ["Products.xlsx"])
        moved = move_file(inbox / "Products.xlsx", PROCESSED)
        self.assertTrue(moved.name.startswith("products_") and moved.suffix == ".xlsx")
        self.assertEqual(moved.parent, self.tmp / PROCESSED)
        self.assertEqual(inbox_files(), [])
        # two files in the same second don't overwrite each other
        shutil.copy(SAMPLES / "wrong_format.txt", inbox / "a.txt")
        shutil.copy(SAMPLES / "wrong_format.txt", inbox / "b.txt")
        first, second = move_file(inbox / "a.txt", FAILED), move_file(inbox / "b.txt", FAILED)
        self.assertNotEqual(first, second)
        self.assertEqual(len(list((self.tmp / FAILED).iterdir())), 2)
