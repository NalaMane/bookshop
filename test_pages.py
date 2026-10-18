"""
Simple tests for the web shop (owner: GP).

Run from the project folder (the one with manage.py):
    python manage.py test test_pages
"""
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse


class PublicPagesTests(TestCase):
    """Pages anyone can open without logging in."""

    def setUp(self):
        # Uses the group's own seed command, so the tests don't depend on model details.
        call_command("seed_books")

    def test_product_list_loads_and_shows_books(self):
        response = self.client.get(reverse("products:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1984")

    def test_login_page_loads(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)

    def test_register_page_loads(self):
        response = self.client.get(reverse("accounts:register"))
        self.assertEqual(response.status_code, 200)

    def test_cart_page_loads(self):
        response = self.client.get(reverse("orders:cart"))
        self.assertEqual(response.status_code, 200)


class LoginRequiredTests(TestCase):
    """Customer pages must send visitors who are not logged in to the login page."""

    def test_order_history_requires_login(self):
        response = self.client.get(reverse("accounts:history"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_profile_requires_login(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_admin_requires_login(self):
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 302)


class LoggedInTests(TestCase):
    """What a logged-in customer can see."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testcustomer", password="test-pass-123"
        )
        self.client.login(username="testcustomer", password="test-pass-123")

    def test_order_history_loads(self):
        response = self.client.get(reverse("accounts:history"))
        self.assertEqual(response.status_code, 200)

    def test_profile_loads(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)


class SharedLayoutTests(TestCase):
    """Checks for templates/base.html and the theme (GP's part)."""

    def test_theme_stylesheet_is_linked(self):
        response = self.client.get(reverse("products:list"))
        self.assertContains(response, "css/theme.css")

    def test_navbar_for_visitor(self):
        response = self.client.get(reverse("products:list"))
        self.assertContains(response, "Log in")
        self.assertContains(response, "Register")
        self.assertNotContains(response, "Log out")

    def test_navbar_for_logged_in_customer(self):
        User.objects.create_user(username="reader", password="test-pass-123")
        self.client.login(username="reader", password="test-pass-123")
        response = self.client.get(reverse("products:list"))
        self.assertContains(response, "Log out")
        self.assertContains(response, "My orders")
        self.assertNotContains(response, "Register")

    def test_staff_sees_admin_link(self):
        User.objects.create_user(
            username="staffer", password="test-pass-123", is_staff=True
        )
        self.client.login(username="staffer", password="test-pass-123")
        response = self.client.get(reverse("products:list"))
        self.assertContains(response, "Admin")
