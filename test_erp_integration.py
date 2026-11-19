"""Lab 3 – end-to-end tests with a FAKE ERP (owner: GP).

Only the HTTP layer is replaced (erp_client's requests session). Everything
else is real: product pages, cart, checkout, erp_client (retries, error
mapping) and the customer lookup. No `cds watch` is needed.

Run from the folder with manage.py:
    python manage.py test test_erp_integration
"""
from decimal import Decimal
from unittest import mock

import requests
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from bookshop import erp_client as erp
from orders.models import Order
from products.models import Product

HOBBIT = "9780547928227"
DUNE = "9780441172719"
DEFAULT_CUSTOMER = "93cada62-c115-47f9-8a06-b56497a60e11"


class FakeResponse:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self._body = body
        self.url = "http://fake-erp"
        self.text = "" if body is None else str(body)
        self.content = b"" if body is None else b"x"

    def json(self):
        if self._body is None:
            raise ValueError
        return self._body


class FakeERP:
    """Very small in-memory ERP: products, customers, orders, createOrder."""

    def __init__(self):
        self.products = [
            {"ID": "uuid-hobbit", "productID": HOBBIT, "name": "The Hobbit", "price": 14.99, "currency": "EUR", "stock": 5},
            {"ID": "uuid-dune", "productID": DUNE, "name": "Dune", "price": 10.50, "currency": "EUR", "stock": 0},
        ]
        self.customers = [{"customerID": "uuid-anna", "name": "Anna", "email": "anna@example.com"}]
        self.orders = []
        self.down = False          # True -> connection error on every call
        self.calls = []            # (method, function)

    def request(self, method, url, json=None, auth=None, timeout=None):
        function = url.rsplit("/", 1)[-1]
        self.calls.append((method, function))
        if self.down:
            raise requests.ConnectionError("fake ERP is down")
        if auth != ("service-user", "service-user"):
            return FakeResponse(401, {"error": {"code": "401", "message": "Unauthorized"}})
        if function == "products()":
            return FakeResponse(200, [dict(p) for p in self.products])
        if function == "customers()":
            return FakeResponse(200, list(self.customers))
        if function == "orders()":
            return FakeResponse(200, list(self.orders))
        if function == "createOrder":
            return self._create_order(json["order"])
        return FakeResponse(404, {"error": {"code": "404", "message": "not found"}})

    def _create_order(self, order):
        by_id = {p["ID"]: p for p in self.products}
        for item in order["items"]:
            product = by_id[item["product"]]
            if item["quantity"] > product["stock"]:
                return FakeResponse(
                    409, {"error": {"code": "409", "message": f"{item['quantity']} exceeds stock for product {product['name']}"}}
                )
        for item in order["items"]:
            by_id[item["product"]]["stock"] -= item["quantity"]
        self.orders.append(
            {
                "orderID": len(self.orders) + 1,
                "customer": order["customer"],
                "orderAmount": order["orderAmount"],
                "orderStatus": "NEW",
            }
        )
        return FakeResponse(204)  # empty answer, like the real ERP

    def call_count(self, function):
        return sum(1 for _, f in self.calls if f == function)


@override_settings(
    ERP_API_URL="http://fake-erp/rest/api",
    ERP_USER="service-user",
    ERP_PASSWORD="service-user",
    ERP_RETRIES=3,
    ERP_RETRY_DELAY=0,
    ERP_DEFAULT_CUSTOMER_ID=DEFAULT_CUSTOMER,
)
class FakeERPTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.erp = FakeERP()
        patcher = mock.patch.object(erp._session, "request", side_effect=self.erp.request)
        patcher.start()
        self.addCleanup(patcher.stop)

        # DB stock is only used by the cart's own check; the ERP stock is what the pages show.
        self.hobbit = Product.objects.create(name="The Hobbit", price="14.99", erp_id=HOBBIT, stock=5)
        self.dune = Product.objects.create(name="Dune", price="10.50", erp_id=DUNE, stock=0)

        self.user = User.objects.create_user("anna", email="anna@example.com", password="test-pass-123")
        self.user.profile.address = "Main Street 1, 52062 Aachen"
        self.user.profile.save()
        self.client.force_login(self.user)

    def put_in_cart(self, product, times=1):
        for _ in range(times):
            self.client.post(reverse("orders:cart_add", args=[product.pk]))


class ProcessAStockTests(FakeERPTestCase):
    """Process A: a customer looks at books -> stock comes from the ERP."""

    def test_list_shows_stock_from_erp(self):
        response = self.client.get(reverse("products:list"))
        self.assertContains(response, "In stock (5 left)")
        self.assertContains(response, "Out of stock")

    def test_list_page_asks_erp_only_once(self):
        self.client.get(reverse("products:list"))
        self.client.get(reverse("products:detail", args=[self.hobbit.pk]))
        self.assertEqual(self.erp.call_count("products()"), 1)  # second page comes from the cache

    def test_erp_down_pages_still_work_with_message(self):
        self.erp.down = True
        response = self.client.get(reverse("products:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The Hobbit")
        self.assertContains(response, "Stock information currently unavailable")

    def test_erp_down_is_retried_three_times(self):
        self.erp.down = True
        self.client.get(reverse("products:list"))
        self.assertEqual(self.erp.call_count("products()"), 3)

    def test_wrong_login_is_not_retried(self):
        with override_settings(ERP_PASSWORD="wrong"):
            response = self.client.get(reverse("products:list"))
        self.assertEqual(response.status_code, 200)  # page works, stock unknown
        self.assertEqual(self.erp.call_count("products()"), 1)  # config error: no retry


class ProcessBCheckoutTests(FakeERPTestCase):
    """Process B: a customer buys -> the order is created in the ERP."""

    def test_successful_checkout_reaches_the_erp(self):
        self.put_in_cart(self.hobbit, times=2)

        response = self.client.post(reverse("orders:checkout"))

        order = Order.objects.get(customer=self.user)
        self.assertRedirects(response, reverse("orders:detail", args=[order.pk]))
        self.assertEqual(order.erp_order_id, 1)  # ID read back from orders()
        self.assertEqual(order.total_price, Decimal("29.98"))
        self.assertEqual(len(self.erp.orders), 1)
        self.assertEqual(self.erp.products[0]["stock"], 3)  # the ERP reduced the stock itself
        self.assertEqual(self.client.session["cart"], {})   # cart emptied

    def test_customer_is_found_by_email(self):
        self.put_in_cart(self.hobbit)
        self.client.post(reverse("orders:checkout"))
        self.assertEqual(self.erp.orders[0]["customer"], "uuid-anna")

    def test_unknown_email_uses_default_customer(self):
        self.user.email = "nobody@example.com"
        self.user.save()
        self.put_in_cart(self.hobbit)
        self.client.post(reverse("orders:checkout"))
        self.assertEqual(self.erp.orders[0]["customer"], DEFAULT_CUSTOMER)

    def test_not_enough_stock_keeps_cart_and_saves_no_order(self):
        self.put_in_cart(self.hobbit, times=3)
        self.erp.products[0]["stock"] = 1  # someone else bought meanwhile

        response = self.client.post(reverse("orders:checkout"), follow=True)

        self.assertRedirects(response, reverse("orders:cart"))
        self.assertContains(response, "exceeds stock")
        self.assertFalse(Order.objects.filter(customer=self.user).exists())
        self.assertEqual(self.client.session["cart"], {str(self.hobbit.pk): 3})
        self.assertEqual(self.erp.orders, [])

    def test_erp_down_at_checkout_shows_message_and_saves_nothing(self):
        self.put_in_cart(self.hobbit)
        self.erp.down = True

        response = self.client.post(reverse("orders:checkout"), follow=True)

        self.assertContains(response, "Orders cannot be placed right now")
        self.assertFalse(Order.objects.filter(customer=self.user).exists())
        self.assertEqual(self.client.session["cart"], {str(self.hobbit.pk): 1})

    def test_checkout_does_not_use_the_stock_cache(self):
        self.client.get(reverse("products:list"))  # fills the 15 s stock cache with "5 left"
        self.put_in_cart(self.hobbit, times=3)
        self.erp.products[0]["stock"] = 1          # ERP changed, cache still says 5

        self.client.post(reverse("orders:checkout"))

        self.assertFalse(Order.objects.filter(customer=self.user).exists())  # the ERP's answer wins

    def test_lost_answer_does_not_create_the_order_twice(self):
        """createOrder worked in the ERP, but the answer got lost -> no second order."""
        self.put_in_cart(self.hobbit)
        original = self.erp.request
        state = {"failed_once": False}

        def flaky(method, url, **kwargs):
            response = original(method, url, **kwargs)
            if url.endswith("createOrder") and not state["failed_once"]:
                state["failed_once"] = True
                raise requests.Timeout("answer lost")
            return response

        with mock.patch.object(erp._session, "request", side_effect=flaky):
            self.client.post(reverse("orders:checkout"))

        self.assertEqual(len(self.erp.orders), 1)
        self.assertEqual(Order.objects.filter(customer=self.user).count(), 1)
