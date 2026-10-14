from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from products.models import Product

from .models import Order


class OrderTests(TestCase):
    def setUp(self):
        self.book = Product.objects.create(name="Dune", price="10.00")
        self.user = User.objects.create_user("anna", password="pass12345")

    def test_checkout_creates_order_with_correct_total(self):
        self.client.login(username="anna", password="pass12345")
        self.client.post(reverse("orders:cart_add", args=[self.book.pk]))
        self.client.post(reverse("orders:cart_add", args=[self.book.pk]))
        self.client.post(reverse("orders:checkout"))
        order = Order.objects.get(customer=self.user)
        self.assertEqual(order.total_price, Decimal("20.00"))
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.items.first().quantity, 2)
