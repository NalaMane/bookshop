from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from bookshop import erp_client as erp

from .models import Product


class ProductTests(TestCase):
    def test_list_shows_books(self):
        Product.objects.create(name="Dune", price="16.99")
        response = self.client.get(reverse("products:list"))
        self.assertContains(response, "Dune")

    def test_only_staff_can_add(self):
        response = self.client.get(reverse("products:create"))
        self.assertEqual(response.status_code, 302)  # redirected to login


# --- Lab 3: live stock from the ERP (Svenja). The ERP is mocked -> no `cds watch` needed.
@mock.patch("products.stock.erp.get_stock_map")
class LiveStockTests(TestCase):
    def setUp(self):
        cache.clear()  # every test starts without cached stock
        self.hobbit = Product.objects.create(name="The Hobbit", price="14.99", erp_id="9780547928227", stock=99)
        self.dune = Product.objects.create(name="Dune", price="10.50", erp_id="9780441172719")
        self.local = Product.objects.create(name="Shop-only book", price="5.00")  # no erp_id

    def test_list_shows_erp_stock_not_db_stock(self, get_stock_map):
        get_stock_map.return_value = {"9780547928227": 24, "9780441172719": 0}
        response = self.client.get(reverse("products:list"))
        self.assertContains(response, "In stock (24 left)")  # from the ERP ...
        self.assertNotContains(response, "99 left")          # ... not the old DB value (99)
        self.assertContains(response, "Out of stock")         # Dune (0) + book not in the ERP

    def test_detail_in_stock(self, get_stock_map):
        get_stock_map.return_value = {"9780547928227": 3}
        response = self.client.get(reverse("products:detail", args=[self.hobbit.pk]))
        self.assertContains(response, "In stock (3 left)")
        self.assertNotContains(response, "disabled>Add to cart")

    def test_detail_out_of_stock_disables_button(self, get_stock_map):
        get_stock_map.return_value = {"9780441172719": 0}
        response = self.client.get(reverse("products:detail", args=[self.dune.pk]))
        self.assertContains(response, "Out of stock")
        self.assertContains(response, "disabled>Add to cart")

    def test_book_not_in_erp_is_out_of_stock(self, get_stock_map):
        get_stock_map.return_value = {"9780547928227": 24}
        response = self.client.get(reverse("products:detail", args=[self.local.pk]))
        self.assertContains(response, "Out of stock")

    def test_erp_down_shows_message_and_page_still_works(self, get_stock_map):
        get_stock_map.side_effect = erp.ERPUnavailable("ERP is not reachable")
        response = self.client.get(reverse("products:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The Hobbit")  # books are still shown
        self.assertContains(response, "Stock information currently unavailable")
        self.assertNotContains(response, "In stock")

    def test_one_erp_call_per_page_and_cache(self, get_stock_map):
        get_stock_map.return_value = {"9780547928227": 24}
        self.client.get(reverse("products:list"))                               # 3 books, 1 ERP call
        self.client.get(reverse("products:detail", args=[self.hobbit.pk]))      # from the cache
        self.assertEqual(get_stock_map.call_count, 1)

    def test_erp_down_is_not_cached(self, get_stock_map):
        get_stock_map.side_effect = [erp.ERPUnavailable("down"), {"9780547928227": 24}]
        self.client.get(reverse("products:list"))
        response = self.client.get(reverse("products:list"))  # ERP is back -> asks again
        self.assertContains(response, "In stock (24 left)")
