from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AccountTests(TestCase):
    def test_register_creates_user_with_address(self):
        self.client.post(reverse("accounts:register"), {
            "username": "anna", "first_name": "Anna", "last_name": "Muster",
            "email": "anna@example.com", "address": "Bayernallee 11, Aachen",
            "password1": "S3cure-pass-123", "password2": "S3cure-pass-123",
        })
        user = User.objects.get(username="anna")
        self.assertEqual(user.profile.address, "Bayernallee 11, Aachen")
