from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


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
