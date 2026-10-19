from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from products.models import Product

from .cart import CART_SESSION_KEY, MAX_ITEM_QUANTITY
from .models import Order


class OrderTests(TestCase):
    def setUp(self):
        self.book = Product.objects.create(name="Dune", price="10.00")
        self.user = User.objects.create_user("anna", password="test-password")
        self.user.profile.address = "Main Street 1, 52062 Aachen"
        self.user.profile.save()

    def test_checkout_creates_order_with_correct_total(self):
        self.client.login(username="anna", password="test-password")
        self.client.post(reverse("orders:cart_add", args=[self.book.pk]))
        self.client.post(reverse("orders:cart_add", args=[self.book.pk]))

        response = self.client.post(reverse("orders:checkout"))

        order = Order.objects.get(customer=self.user)
        self.assertEqual(order.total_price, Decimal("20.00"))
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.items.first().quantity, 2)
        self.assertRedirects(response, reverse("products:list"))

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
