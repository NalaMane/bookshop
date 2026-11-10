"""Tests for erp_client.py (Nala) – the ERP is mocked, so `cds watch` is NOT needed.

Run: python manage.py test bookshop
"""
from decimal import Decimal
from unittest import mock

import requests
from django.test import SimpleTestCase, override_settings

from bookshop import erp_client as erp

PRODUCTS = [
    {"ID": "uuid-hobbit", "productID": "9780547928227", "name": "The Hobbit", "price": 14.99, "currency": "EUR", "stock": 24},
    {"ID": "uuid-dune", "productID": "9780441172719", "name": "Dune", "price": 10.5, "currency": "EUR", "stock": 0},
]
CUSTOMERS = [{"customerID": "uuid-drumm", "name": "Christian Drumm", "email": "drumm@fh-aachen.de"}]


def response(status=200, json=None, text=""):
    r = mock.Mock(status_code=status, url="http://erp/test", text=text)
    r.content = b"x" if (json is not None or text) else b""
    r.json.return_value = json
    if json is None:
        r.json.side_effect = ValueError
    return r


@override_settings(ERP_RETRY_DELAY=0, ERP_RETRIES=3)
class ERPClientTests(SimpleTestCase):
    def setUp(self):
        patcher = mock.patch.object(erp._session, "request")
        self.request = patcher.start()
        self.addCleanup(patcher.stop)

    # --- stock
    def test_get_stock(self):
        self.request.return_value = response(json=PRODUCTS)
        self.assertEqual(erp.get_stock("9780547928227"), 24)
        self.assertEqual(erp.get_stock("9780441172719"), 0)
        self.assertIsNone(erp.get_stock("0000000000000"))

    def test_uses_basic_auth_and_timeout(self):
        self.request.return_value = response(json=PRODUCTS)
        erp.get_products()
        _, kwargs = self.request.call_args
        self.assertEqual(kwargs["auth"], ("service-user", "service-user"))
        self.assertIn("timeout", kwargs)

    def test_stock_map_and_decimal_price(self):
        self.request.return_value = response(json=PRODUCTS)
        self.assertEqual(erp.get_stock_map(), {"9780547928227": 24, "9780441172719": 0})
        self.assertEqual(erp.get_product("9780547928227")["price"], Decimal("14.99"))

    # --- retries
    def test_retries_then_succeeds(self):
        self.request.side_effect = [requests.ConnectionError(), requests.Timeout(), response(json=PRODUCTS)]
        self.assertEqual(erp.get_stock("9780547928227"), 24)
        self.assertEqual(self.request.call_count, 3)

    def test_gives_up_after_3_tries(self):
        self.request.side_effect = requests.ConnectionError()
        with self.assertRaises(erp.ERPUnavailable):
            erp.get_products()
        self.assertEqual(self.request.call_count, 3)

    def test_500_is_retried(self):
        self.request.side_effect = [response(500, text="boom"), response(json=PRODUCTS)]
        self.assertEqual(len(erp.get_products()), 2)

    def test_401_not_retried(self):
        self.request.return_value = response(401, text="Unauthorized")
        with self.assertRaises(erp.ERPConfigError):
            erp.get_products()
        self.assertEqual(self.request.call_count, 1)

    # --- customers
    def test_find_customer_by_email(self):
        self.request.return_value = response(json=CUSTOMERS)
        self.assertEqual(erp.find_customer(" Drumm@FH-Aachen.de "), "uuid-drumm")
        self.assertIsNone(erp.find_customer("nobody@example.com"))
        self.assertIsNone(erp.find_customer(""))

    # --- orders
    def test_create_order(self):
        new_order = {"orderID": 6, "customer": "uuid-drumm", "orderAmount": 29.98, "items": []}
        self.request.side_effect = [
            response(json=PRODUCTS),            # products()  -> map ISBN to UUID
            response(json=[{"orderID": 5}]),    # orders()    -> highest ID before
            response(204),                      # createOrder -> empty answer
            response(json=[{"orderID": 5}, new_order]),  # orders() -> find new ID
        ]
        self.assertEqual(erp.create_order("uuid-drumm", [("9780547928227", 2)]), 6)

        method, url = self.request.call_args_list[2].args
        payload = self.request.call_args_list[2].kwargs["json"]["order"]
        self.assertEqual((method, url.rsplit("/", 1)[1]), ("POST", "createOrder"))
        self.assertEqual(payload["customer"], "uuid-drumm")
        self.assertEqual(payload["orderAmount"], 29.98)
        self.assertEqual(payload["items"], [{"product": "uuid-hobbit", "quantity": 2, "itemAmount": 29.98, "currency": "EUR"}])

    def test_create_order_not_enough_stock(self):
        self.request.side_effect = [
            response(json=PRODUCTS),
            response(json=[]),
            response(409, json={"error": {"code": "409", "message": "100 exceeds stock for product #9780547928227"}}),
        ]
        with self.assertRaises(erp.InsufficientStock) as ctx:
            erp.create_order("uuid-drumm", [("9780547928227", 100)])
        self.assertIn("exceeds stock", ctx.exception.message)
        self.assertEqual(self.request.call_count, 3)  # 409 is not retried

    def test_create_order_unknown_isbn(self):
        self.request.return_value = response(json=PRODUCTS)
        with self.assertRaises(erp.ERPBusinessError):
            erp.create_order("uuid-drumm", [("0000000000000", 1)])

    def test_create_order_no_duplicate_on_lost_answer(self):
        """The ERP saved the order but the answer timed out -> no second createOrder."""
        new_order = {"orderID": 1, "customer": "uuid-drumm", "orderAmount": 14.99}
        self.request.side_effect = [
            response(json=PRODUCTS),
            response(json=[]),
            requests.Timeout(),                # createOrder: answer lost
            response(json=[new_order]),        # orders(): it's there
        ]
        self.assertEqual(erp.create_order("uuid-drumm", [("9780547928227", 1)]), 1)
        posts = [c for c in self.request.call_args_list if c.args[0] == "POST"]
        self.assertEqual(len(posts), 1)

    def test_create_order_retries_when_first_try_did_not_arrive(self):
        new_order = {"orderID": 1, "customer": "uuid-drumm", "orderAmount": 14.99}
        self.request.side_effect = [
            response(json=PRODUCTS),
            response(json=[]),
            requests.ConnectionError(),        # createOrder try 1 fails
            response(json=[]),                 # orders(): not there -> retry
            response(204),                     # createOrder try 2 OK
            response(json=[new_order]),
        ]
        self.assertEqual(erp.create_order("uuid-drumm", [("9780547928227", 1)]), 1)

    def test_is_available(self):
        self.request.return_value = response(json=CUSTOMERS)
        self.assertTrue(erp.is_available())
        self.request.side_effect = requests.ConnectionError()
        self.assertFalse(erp.is_available())
