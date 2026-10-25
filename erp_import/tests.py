"""Tests for the ERP upload page (owner: GP).

End-to-end tests with Ami's sample files come later, once her files and
Svenja's import code are in the project.
"""
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse


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

    def test_wrong_file_type_is_rejected(self):
        wrong = SimpleUploadedFile("products.txt", b"not excel")
        response = self.client.post(self.url, {"erp_file": wrong})
        self.assertContains(response, "Only .xlsx files can be imported.")

    def test_xlsx_is_saved_to_inbox_and_import_is_started(self):
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
