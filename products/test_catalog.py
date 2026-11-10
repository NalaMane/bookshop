"""Lab 3 – tests for the automatic ERP catalog sync (owner: Ami). ERP mocked, no `cds watch` needed.

Run: python manage.py test products
"""
from decimal import Decimal
from io import StringIO
from unittest import mock

from django.core.cache import cache
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from bookshop import erp_client as erp

from .catalog import sync_catalog, sync_catalog_if_due
from .models import Product

HOBBIT = {"ID": "u1", "productID": "9780547928227", "name": "The Hobbit", "description": None,
          "price": Decimal("14.90"), "currency": "EUR", "stock": 15}
HARRY = {"ID": "u2", "productID": "9780590353427", "name": "Harry Potter and the Sorcerer's Stone",
         "description": "A fantasy novel by J.K. Rowling.", "price": Decimal("12.99"), "currency": "EUR", "stock": 20}


class SyncCatalogTests(TestCase):
    def test_creates_new_erp_books_with_cover_but_no_stock(self):
        self.assertEqual(sync_catalog([HARRY]), (1, 0))
        book = Product.objects.get(erp_id="9780590353427")
        self.assertEqual((book.name, book.price), ("Harry Potter and the Sorcerer's Stone", Decimal("12.99")))
        self.assertIn("9780590353427", book.cover_url)
        self.assertIsNone(book.stock)  # stock is only read live from the ERP

    def test_updates_existing_book_by_isbn_without_duplicates(self):
        Product.objects.create(name="Hobbit (old name)", price="9.99", erp_id="9780547928227",
                               author="J.R.R. Tolkien", description="Shop text")
        self.assertEqual(sync_catalog([HOBBIT]), (0, 1))
        book = Product.objects.get()
        self.assertEqual((book.name, book.price), ("The Hobbit", Decimal("14.90")))
        self.assertEqual((book.author, book.description), ("J.R.R. Tolkien", "Shop text"))  # shop-only data kept

    def test_nothing_changed_nothing_saved(self):
        sync_catalog([HOBBIT])
        self.assertEqual(sync_catalog([HOBBIT]), (0, 0))

    def test_book_missing_in_erp_is_not_deleted(self):
        Product.objects.create(name="Old book", price="5.00", erp_id="9780000000002")
        sync_catalog([HOBBIT])
        self.assertTrue(Product.objects.filter(erp_id="9780000000002").exists())

    def test_incomplete_erp_product_is_skipped(self):
        self.assertEqual(sync_catalog([{"productID": "", "name": "No ID", "price": Decimal("1")}, HOBBIT]), (1, 0))


@override_settings(ERP_CATALOG_SYNC_SECONDS=60)
class AutomaticSyncTests(TestCase):
    def setUp(self):
        cache.clear()

    @mock.patch("products.stock.erp.get_stock_map", return_value={"9780590353427": 20})
    @mock.patch("products.catalog.erp.get_products", return_value=[HARRY])
    def test_book_list_loads_new_erp_book_by_itself(self, get_products, _):
        response = self.client.get(reverse("products:list"))
        self.assertContains(response, "Harry Potter and the Sorcerer")  # visible on the first visit
        self.assertContains(response, "In stock (20 left)")
        self.client.get(reverse("products:list"))
        self.assertEqual(get_products.call_count, 1)  # second visit within 60 s: no new sync

    @mock.patch("products.catalog.erp.get_products", side_effect=erp.ERPUnavailable("down"))
    def test_erp_down_does_not_break_and_is_not_retried_every_visit(self, get_products):
        self.assertIsNone(sync_catalog_if_due())
        self.assertIsNone(sync_catalog_if_due())
        self.assertEqual(get_products.call_count, 1)

    @override_settings(ERP_CATALOG_SYNC_SECONDS=0)
    @mock.patch("products.catalog.erp.get_products")
    def test_can_be_switched_off(self, get_products):
        sync_catalog_if_due()
        get_products.assert_not_called()


class SyncCommandTests(TestCase):
    @mock.patch("products.catalog.erp.get_products", return_value=[HOBBIT, HARRY])
    def test_command(self, _):
        out = StringIO()
        call_command("sync_products", stdout=out)
        self.assertIn("2 created, 0 updated", out.getvalue())

    @mock.patch("products.catalog.erp.get_products", side_effect=erp.ERPUnavailable("ERP is not reachable"))
    def test_command_erp_down(self, _):
        with self.assertRaises(CommandError):
            call_command("sync_products")
