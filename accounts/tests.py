from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from orders.cart import CART_SESSION_KEY


class AccountTests(TestCase):
    def test_register_creates_user_with_address(self):
        self.client.post(reverse("accounts:register"), {
            "username": "anna", "first_name": "Anna", "last_name": "Muster",
            "email": "anna@example.com", "street": "Bayernallee 11", "postal_code": "52066", "city": "Aachen",
            "password1": "S3cure-pass-123", "password2": "S3cure-pass-123",
        })
        user = User.objects.get(username="anna")
        self.assertEqual(user.profile.street, "Bayernallee 11")
        self.assertEqual(user.profile.postal_code, "52066")
        self.assertEqual(user.profile.city, "Aachen")

    def test_logout_and_login_keep_cart(self):
        user = User.objects.create_user(
            "anna",
            "anna@example.com",
            "test-password",
        )
        self.client.force_login(user)
        session = self.client.session
        session[CART_SESSION_KEY] = {"7": 3}
        session.save()

        response = self.client.post(reverse("accounts:logout"))

        self.assertRedirects(response, reverse("products:list"))

        login = self.client.post(reverse("accounts:login"), {
            "username": "anna",
            "password": "test-password",
        })
        self.assertEqual(login.status_code, 302)
        self.assertEqual(self.client.session[CART_SESSION_KEY], {"7": 3})
