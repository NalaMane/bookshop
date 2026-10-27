"""Lab 2 – tests for the import into the shop (importer.py) and the fixes from 27.10.

Run: python manage.py test erp_import
"""
import tempfile
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from products.models import Product

from .importer import import_rows, isbn_from
from .models import ImportLog

HOBBIT_ISBN = "9780547928227"


def row(erp_id=HOBBIT_ISBN, name="The Hobbit", description="", price="12.99", stock=15):
    return {"erp_id": erp_id, "name": name, "description": description,
            "price": Decimal(price), "stock": stock}


class ImporterTests(TestCase):
    def test_creates_new_book(self):
        self.assertEqual(import_rows([row()]), (1, 0))
        book = Product.objects.get(erp_id=HOBBIT_ISBN)
        self.assertEqual((book.name, book.price, book.stock), ("The Hobbit", Decimal("12.99"), 15))

    def test_updates_existing_book_by_erp_id(self):
        import_rows([row()])
        self.assertEqual(import_rows([row(price="9.99", stock=0)]), (0, 1))
        book = Product.objects.get()
        self.assertEqual((book.price, book.stock), (Decimal("9.99"), 0))

    def test_links_old_book_with_same_name_instead_of_duplicate(self):
        old = Product.objects.create(name="the hobbit ", author="J.R.R. Tolkien", price="14.90",
                                     cover_url="https://example.com/hobbit.jpg")
        self.assertEqual(import_rows([row()]), (0, 1))
        self.assertEqual(Product.objects.count(), 1)
        old.refresh_from_db()
        self.assertEqual((old.erp_id, old.stock), (HOBBIT_ISBN, 15))
        self.assertEqual(old.author, "J.R.R. Tolkien")  # shop-only data is kept
        self.assertEqual(old.cover_url, "https://example.com/hobbit.jpg")

    def test_does_not_guess_when_two_old_books_have_the_same_name(self):
        Product.objects.create(name="The Hobbit", price="10")
        Product.objects.create(name="The Hobbit", price="11")
        self.assertEqual(import_rows([row()]), (1, 0))
        self.assertEqual(Product.objects.filter(erp_id=HOBBIT_ISBN).count(), 1)

    def test_empty_erp_description_keeps_shop_description(self):
        Product.objects.create(name="The Hobbit", erp_id=HOBBIT_ISBN, price="12.99", stock=1,
                               description="Bilbo Baggins sets off on an unexpected journey.")
        import_rows([row(description="")])
        self.assertEqual(Product.objects.get().description, "Bilbo Baggins sets off on an unexpected journey.")
        import_rows([row(description="New text from the ERP")])
        self.assertEqual(Product.objects.get().description, "New text from the ERP")

    def test_cover_from_isbn_content_enricher(self):
        import_rows([row(), row(erp_id="BOOK1001", name="1984")])
        self.assertIn(HOBBIT_ISBN, Product.objects.get(erp_id=HOBBIT_ISBN).cover_url)
        self.assertEqual(Product.objects.get(erp_id="BOOK1001").cover_url, "")  # not an ISBN -> no cover

    def test_isbn_detection(self):
        self.assertEqual(isbn_from("978-0-547-92822-7"), HOBBIT_ISBN)
        self.assertEqual(isbn_from("0547928220"), "0547928220")
        self.assertIsNone(isbn_from("BOOK1001"))
        self.assertIsNone(isbn_from("DXTR1000"))

    def test_all_or_nothing(self):
        rows = [row(), row(erp_id="X2", name="Second", price="1")]
        with patch.object(Product, "save", side_effect=[None, RuntimeError("database down")]):
            with self.assertRaises(RuntimeError):
                import_rows(rows)
        self.assertEqual(Product.objects.count(), 0)


class ProductFormTests(TestCase):
    def setUp(self):
        User.objects.create_user("staffer", password="pw", is_staff=True)
        self.client.login(username="staffer", password="pw")

    def test_form_saves_stock_and_erp_id(self):
        self.client.post(reverse("products:create"), {"name": "Dune", "price": "16.99", "stock": "4",
                                                      "erp_id": "9780441172719"})
        book = Product.objects.get(name="Dune")
        self.assertEqual((book.stock, book.erp_id), (4, "9780441172719"))

    def test_stock_is_required_and_empty_erp_id_is_none(self):
        response = self.client.post(reverse("products:create"), {"name": "A", "price": "5", "stock": ""})
        self.assertFalse(Product.objects.exists())
        self.assertContains(response, "required")
        self.client.post(reverse("products:create"), {"name": "A", "price": "5", "stock": "1", "erp_id": " "})
        self.client.post(reverse("products:create"), {"name": "B", "price": "5", "stock": "1", "erp_id": ""})
        self.assertEqual(Product.objects.filter(erp_id__isnull=True).count(), 2)


class StockLimitStaysOnPageTests(TestCase):
    def test_stock_error_stays_on_the_same_page(self):
        book = Product.objects.create(name="Dune", price="10", stock=0)
        response = self.client.post(reverse("orders:cart_add", args=[book.pk]),
                                    HTTP_REFERER="/?q=dune")
        self.assertRedirects(response, "/?q=dune", fetch_redirect_response=False)


class UploadShowsOnlyItsOwnLogTests(TestCase):
    def test_old_log_is_not_shown_when_import_fails(self):
        ImportLog.record("old_file.xlsx", created=5)
        User.objects.create_user("staffer", password="pw", is_staff=True)
        self.client.login(username="staffer", password="pw")
        with tempfile.TemporaryDirectory() as tmp, override_settings(ERP_EXCHANGE_DIR=tmp):
            with patch("erp_import.views.call_command", side_effect=RuntimeError("boom")):
                response = self.client.post(reverse("erp_import:upload"),
                                            {"erp_file": SimpleUploadedFile("new.xlsx", b"x")})
        self.assertContains(response, "Import failed: boom")
        self.assertNotContains(response, "<td>5</td>")  # result of the old file is not shown
