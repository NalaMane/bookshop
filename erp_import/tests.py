"""Tests for the ERP import (owner: GP).

Part 1: upload page (access, saving the file, showing the result).
Part 2: Ami's validation, run on the real sample files in erp_exchange/samples/.
Part 3: ImportLog status logic.
"""
import re
import tempfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .models import ImportLog
from .validation import InvalidFileError, read_and_validate


# ------------------------------------------------------------------ upload page

class UploadAccessTests(TestCase):
    def test_visitor_is_sent_to_login(self):
        response = self.client.get(reverse("erp_import:upload"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_customer_is_sent_to_login(self):
        User.objects.create_user(username="customer", password="test-pass-123")
        self.client.login(username="customer", password="test-pass-123")
        response = self.client.get(reverse("erp_import:upload"))
        self.assertEqual(response.status_code, 302)

    def test_staff_can_open_page(self):
        User.objects.create_user(username="staffer", password="test-pass-123", is_staff=True)
        self.client.login(username="staffer", password="test-pass-123")
        response = self.client.get(reverse("erp_import:upload"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Import ERP file")


class UploadBehaviourTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="staffer", password="test-pass-123", is_staff=True)
        self.client.login(username="staffer", password="test-pass-123")
        self.url = reverse("erp_import:upload")

    def test_no_file_shows_error(self):
        response = self.client.post(self.url, {})
        self.assertContains(response, "Please choose a file first.")

    def test_file_is_saved_to_inbox_and_import_is_started(self):
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(ERP_EXCHANGE_DIR=tmp):
                with patch("erp_import.views.call_command") as fake_import:
                    good = SimpleUploadedFile("erp.xlsx", b"placeholder")
                    response = self.client.post(self.url, {"erp_file": good})
                saved = list((Path(tmp) / "inbox").glob("*erp.xlsx"))
        self.assertEqual(len(saved), 1)
        fake_import.assert_called_once()
        self.assertEqual(fake_import.call_args[0][0], "import_products")
        self.assertContains(response, "Import finished.")

    def test_result_table_shows_the_import_log(self):
        def fake_import(*args, **kwargs):
            ImportLog.record("erp.xlsx", created=2, updated=1, errors=["Row 4: Price is missing"])

        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(ERP_EXCHANGE_DIR=tmp):
                with patch("erp_import.views.call_command", side_effect=fake_import):
                    good = SimpleUploadedFile("erp.xlsx", b"placeholder")
                    response = self.client.post(self.url, {"erp_file": good})
        self.assertContains(response, "Partial")
        self.assertContains(response, "Row 4: Price is missing")


# ------------------------------------------------- validation on the sample files

SAMPLES = Path(settings.ERP_EXCHANGE_DIR) / "samples"


class SampleFileValidationTests(SimpleTestCase):
    def ids(self, rows):
        return {row["erp_id"] for row in rows}

    def test_valid_export(self):
        rows, errors = read_and_validate(SAMPLES / "valid_erp_export.xlsx")
        self.assertEqual(self.ids(rows), {"9780547928227", "9780451524935"})
        self.assertEqual(errors, [])

    def test_updated_export_contains_the_changes(self):
        rows, errors = read_and_validate(SAMPLES / "updated_erp_export.xlsx")
        by_id = {row["erp_id"]: row for row in rows}
        self.assertEqual(errors, [])
        self.assertEqual(by_id["9780451524935"]["price"], Decimal("8.99"))
        self.assertEqual(by_id["9780547928227"]["stock"], 0)
        self.assertIn("9780441172719", by_id)

    def test_rows_with_errors_are_skipped_and_good_rows_kept(self):
        rows, errors = read_and_validate(SAMPLES / "export_with_errors.xlsx")
        self.assertEqual(self.ids(rows), {"9780451524935", "9780141439518"})
        bad_rows = {m.group(1) for m in map(re.compile(r"^Row (\d+):").match, errors) if m}
        self.assertEqual(len(bad_rows), 7)

    def test_csv_with_semicolons_and_decimal_comma(self):
        rows, errors = read_and_validate(SAMPLES / "valid_export.csv")
        self.assertEqual(len(rows), 2)
        self.assertEqual(errors, [])

    def test_missing_column_rejects_whole_file(self):
        with self.assertRaises(InvalidFileError) as caught:
            read_and_validate(SAMPLES / "missing_columns.xlsx")
        self.assertIn("Stock", str(caught.exception))

    def test_empty_export_is_rejected(self):
        with self.assertRaises(InvalidFileError):
            read_and_validate(SAMPLES / "empty_export.xlsx")

    def test_wrong_file_type_is_rejected(self):
        with self.assertRaises(InvalidFileError) as caught:
            read_and_validate(SAMPLES / "wrong_format.txt")
        self.assertIn("Wrong file type", str(caught.exception))

    def test_fake_excel_file_is_rejected(self):
        with self.assertRaises(InvalidFileError):
            read_and_validate(SAMPLES / "not_really_excel.xlsx")


# ------------------------------------------------------------ import log status

class ImportLogStatusTests(TestCase):
    def test_no_errors_is_success(self):
        log = ImportLog.record("a.xlsx", created=2, updated=1)
        self.assertEqual(log.status, ImportLog.Status.SUCCESS)

    def test_some_errors_with_imports_is_partial(self):
        log = ImportLog.record("a.xlsx", created=2, errors=["Row 3: x", "Row 3: y", "Row 5: z"])
        self.assertEqual(log.status, ImportLog.Status.PARTIAL)
        self.assertEqual(log.failed_count, 2)  # row 3 counts once

    def test_errors_and_nothing_imported_is_failed(self):
        log = ImportLog.record("a.xlsx", errors=["Row 3: x"])
        self.assertEqual(log.status, ImportLog.Status.FAILED)

    def test_rejected_file_is_failed(self):
        log = ImportLog.record("a.txt", file_error="Wrong file type")
        self.assertEqual(log.status, ImportLog.Status.FAILED)
        self.assertEqual(log.errors, ["Wrong file type"])
