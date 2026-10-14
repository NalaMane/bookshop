from django.test import TestCase
from django.urls import reverse

from .models import Product


class ProductTests(TestCase):
    def test_list_shows_books(self):
        Product.objects.create(name="Dune", price="16.99")
        response = self.client.get(reverse("products:list"))
        self.assertContains(response, "Dune")

    def test_only_staff_can_add(self):
        response = self.client.get(reverse("products:create"))
        self.assertEqual(response.status_code, 302)  # redirected to login
