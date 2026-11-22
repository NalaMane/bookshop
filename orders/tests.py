from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from products.models import Product

from bookshop import erp_client as erp

from .cart import CART_SESSION_KEY, MAX_ITEM_QUANTITY
from .models import Order
from . import views


class OrderTests(TestCase):
    def setUp(self):
        self.book = Product.objects.create(name="Dune", price="10.00", stock=10)
        self.user = User.objects.create_user("anna", password="test-password")
        self.user.profile.address = "Main Street 1, 52062 Aachen"
        self.user.profile.save()
        def set_local_stock_as_live(products):
            for product in products:
                product.live_stock = product.stock
            return True

        self.live_cart_stock = mock.patch(
            "orders.cart.add_live_stock",
            side_effect=set_local_stock_as_live,
        )
        self.live_view_stock = mock.patch(
            "orders.views.add_live_stock",
            side_effect=set_local_stock_as_live,
        )
        self.live_cart_stock.start()
        self.live_view_stock.start()
        self.addCleanup(self.live_cart_stock.stop)
        self.addCleanup(self.live_view_stock.stop)
        self.erp_customer = mock.patch.object(
            views, "erp_customer_for", return_value=SimpleNamespace(id="erp-customer")
        )
        self.create_erp_order = mock.patch.object(erp, "create_order", return_value=42)
        self.erp_customer.start()
        self.create_erp_order.start()
        self.addCleanup(self.erp_customer.stop)
        self.addCleanup(self.create_erp_order.stop)

    def test_checkout_creates_order_with_correct_total(self):
        self.client.login(username="anna", password="test-password")
        self.client.post(reverse("orders:cart_add", args=[self.book.pk]))
        self.client.post(reverse("orders:cart_add", args=[self.book.pk]))

        response = self.client.post(reverse("orders:checkout"))

        order = Order.objects.get(customer=self.user)
        self.assertEqual(order.total_price, Decimal("20.00"))
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.items.first().quantity, 2)
        self.book.refresh_from_db()
        self.assertEqual(self.book.stock, 10)
        self.assertEqual(order.erp_order_id, 42)
        self.assertRedirects(response, reverse("orders:detail", args=[order.pk]))

    def test_checkout_allows_reused_erp_order_id_after_erp_restart(self):
        existing = Order.objects.create(
            customer=self.user,
            shipping_address="Existing address",
            erp_order_id=42,
        )
        self.client.force_login(self.user)
        self.client.post(reverse("orders:cart_add", args=[self.book.pk]))

        response = self.client.post(reverse("orders:checkout"))

        new_order = Order.objects.exclude(pk=existing.pk).get(customer=self.user)
        self.assertEqual(new_order.erp_order_id, 42)
        self.assertRedirects(response, reverse("orders:detail", args=[new_order.pk]))

    def test_out_of_stock_product_cannot_be_added(self):
        self.book.stock = 0
        self.book.save(update_fields=["stock"])

        response = self.client.post(reverse("orders:cart_add", args=[self.book.pk]))

        self.assertRedirects(response, reverse("orders:cart"))
        self.assertEqual(self.client.session.get(CART_SESSION_KEY, {}), {})

    def test_product_without_stock_value_cannot_be_added(self):
        self.book.stock = None
        self.book.save(update_fields=["stock"])

        self.client.post(reverse("orders:cart_add", args=[self.book.pk]))

        self.assertEqual(self.client.session.get(CART_SESSION_KEY, {}), {})

    def test_ajax_cart_add_returns_cart_state(self):
        response = self.client.post(
            reverse("orders:cart_add", args=[self.book.pk]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "success": True,
                "message": '"Dune" added to cart.',
                "cart_count": 1,
                "quantity": 1,
                "stock": 10,
            },
        )

    def test_cart_page_uses_erp_stock_when_local_stock_is_empty(self):
        self.book.erp_id = "9780441172719"
        self.book.stock = None
        self.book.save(update_fields=["erp_id", "stock"])
        self.client.force_login(self.user)
        session = self.client.session
        session[CART_SESSION_KEY] = {str(self.book.pk): 2}
        session.save()

        with mock.patch("orders.views.add_live_stock") as live_stock:
            live_stock.side_effect = lambda products: setattr(
                products[0], "live_stock", 10
            ) or True
            response = self.client.get(reverse("orders:cart"))

        self.assertContains(response, "10 in stock")
        self.assertNotContains(response, "No longer available")

    def test_ajax_cart_update_returns_stock_error_without_redirect(self):
        self.client.post(reverse("orders:cart_add", args=[self.book.pk]))
        response = self.client.post(
            reverse("orders:cart_update", args=[self.book.pk]),
            {"quantity": 11},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["success"], False)
        self.assertIn("Only 10", response.json()["message"])
        self.assertEqual(response.json()["cart_count"], 1)

    def test_ajax_cart_plus_updates_quantity_and_subtotal(self):
        self.client.post(reverse("orders:cart_add", args=[self.book.pk]))

        response = self.client.post(
            reverse("orders:cart_update", args=[self.book.pk]),
            {"quantity": 2},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["quantity"], 2)
        self.assertEqual(response.json()["subtotal"], "20.00")
        self.assertEqual(response.json()["total"], "20.00")
        self.assertEqual(
            self.client.session[CART_SESSION_KEY],
            {str(self.book.pk): 2},
        )

    def test_ajax_cart_minus_updates_quantity_and_subtotal(self):
        self.client.post(reverse("orders:cart_add", args=[self.book.pk]))
        self.client.post(
            reverse("orders:cart_update", args=[self.book.pk]),
            {"quantity": 2},
        )
        response = self.client.post(
            reverse("orders:cart_update", args=[self.book.pk]),
            {"quantity": 1},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["quantity"], 1)
        self.assertEqual(response.json()["subtotal"], "10.00")
        self.assertEqual(response.json()["total"], "10.00")

    def test_cart_quantity_cannot_exceed_stock(self):
        self.book.stock = 2
        self.book.save(update_fields=["stock"])
        self.client.post(reverse("orders:cart_add", args=[self.book.pk]))
        self.client.post(reverse("orders:cart_add", args=[self.book.pk]))

        response = self.client.post(
            reverse("orders:cart_add", args=[self.book.pk])
        )

        self.assertRedirects(response, reverse("orders:cart"))
        self.assertEqual(
            self.client.session[CART_SESSION_KEY],
            {str(self.book.pk): 2},
        )

    def test_cart_update_cannot_exceed_stock(self):
        self.book.stock = 2
        self.book.save(update_fields=["stock"])
        self.client.post(reverse("orders:cart_add", args=[self.book.pk]))

        self.client.post(
            reverse("orders:cart_update", args=[self.book.pk]),
            {"quantity": 3},
        )

        self.assertEqual(
            self.client.session[CART_SESSION_KEY],
            {str(self.book.pk): 1},
        )

    def test_checkout_rejects_stock_that_changed_after_add(self):
        self.client.force_login(self.user)
        self.client.post(reverse("orders:cart_add", args=[self.book.pk]))
        self.create_erp_order.stop()
        self.create_erp_order = mock.patch.object(
            erp,
            "create_order",
            side_effect=erp.InsufficientStock("Only 0 left in stock."),
        )
        self.create_erp_order.start()
        self.addCleanup(self.create_erp_order.stop)

        response = self.client.post(reverse("orders:checkout"))

        self.assertRedirects(response, reverse("orders:cart"))
        self.assertFalse(Order.objects.filter(customer=self.user).exists())
        self.book.refresh_from_db()
        self.assertEqual(self.book.stock, 10)

    def test_cart_update_rejects_invalid_quantity(self):
        self.client.post(reverse("orders:cart_add", args=[self.book.pk]))

        response = self.client.post(
            reverse("orders:cart_update", args=[self.book.pk]),
            {"quantity": "not-a-number"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session[CART_SESSION_KEY], {str(self.book.pk): 1})

    def test_cart_update_rejects_negative_quantity(self):
        self.client.post(reverse("orders:cart_add", args=[self.book.pk]))

        self.client.post(reverse("orders:cart_update", args=[self.book.pk]), {"quantity": -1})

        self.assertEqual(self.client.session[CART_SESSION_KEY], {str(self.book.pk): 1})

    def test_cart_update_rejects_quantity_above_limit(self):
        self.client.post(reverse("orders:cart_add", args=[self.book.pk]))

        self.client.post(
            reverse("orders:cart_update", args=[self.book.pk]),
            {"quantity": MAX_ITEM_QUANTITY + 1},
        )

        self.assertEqual(self.client.session[CART_SESSION_KEY], {str(self.book.pk): 1})

    def test_deleted_product_is_removed_from_cart(self):
        session = self.client.session
        session[CART_SESSION_KEY] = {str(self.book.pk): 1}
        session.save()
        self.book.delete()

        response = self.client.get(reverse("orders:cart"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session[CART_SESSION_KEY], {})

    def test_checkout_requires_shipping_address(self):
        self.user.profile.address = ""
        self.user.profile.save()
        self.client.force_login(self.user)
        self.client.post(reverse("orders:cart_add", args=[self.book.pk]))

        response = self.client.post(reverse("orders:checkout"))

        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertFalse(Order.objects.filter(customer=self.user).exists())

    def test_empty_cart_cannot_be_checked_out(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("orders:checkout"))

        self.assertRedirects(response, reverse("orders:cart"))
