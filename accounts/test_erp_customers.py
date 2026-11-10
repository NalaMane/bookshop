"""Lab 3 – tests for the ERP customer lookup (owner: Ami). The ERP is mocked, no `cds watch` needed.

Run: python manage.py test accounts
"""
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from bookshop import erp_client as erp

from .erp_customers import ERPCustomer, erp_customer_for, erp_link_status

DEFAULT_ID = "default-webshop-customer"


@override_settings(ERP_DEFAULT_CUSTOMER_ID=DEFAULT_ID)
class ERPCustomerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("anna", "Anna@Example.com", "pw-12345!")

    @mock.patch.object(erp, "find_customer", return_value="uuid-anna")
    def test_found_by_email(self, find_customer):
        self.assertEqual(erp_customer_for(self.user), ERPCustomer("uuid-anna", matched=True))
        find_customer.assert_called_once_with(self.user.email)

    @mock.patch.object(erp, "find_customer", return_value=None)
    def test_not_in_erp_uses_default_customer(self, _):
        self.assertEqual(erp_customer_for(self.user), ERPCustomer(DEFAULT_ID, matched=False))

    @mock.patch.object(erp, "find_customer", side_effect=erp.ERPUnavailable("down"))
    def test_erp_down_is_passed_on_to_checkout(self, _):
        with self.assertRaises(erp.ERPError):
            erp_customer_for(self.user)

    def test_lookup_ignores_upper_and_lower_case(self):
        customers = [{"customerID": "uuid-anna", "email": "anna@example.com"}]
        with mock.patch.object(erp, "get_customers", return_value=customers):
            self.assertEqual(erp_customer_for(self.user).id, "uuid-anna")


@override_settings(ERP_DEFAULT_CUSTOMER_ID=DEFAULT_ID)
class ProfileERPStatusTests(TestCase):
    """The profile page shows the ERP link and still works when the ERP is down."""

    def setUp(self):
        self.user = User.objects.create_user("anna", "anna@example.com", "pw-12345!")
        self.client.force_login(self.user)
        patcher = mock.patch.object(erp, "is_available", return_value=True)
        self.is_available = patcher.start()
        self.addCleanup(patcher.stop)

    def profile_text(self):
        response = self.client.get("/accounts/profile/")
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    @mock.patch.object(erp, "find_customer", return_value="uuid-anna")
    def test_linked(self, _):
        self.assertIn("linked to your customer account in our ERP", self.profile_text())

    @mock.patch.object(erp, "find_customer", return_value=None)
    def test_not_linked(self, _):
        self.assertIn("general web shop customer", self.profile_text())

    def test_erp_down(self):
        self.is_available.return_value = False
        with mock.patch.object(erp, "find_customer") as find_customer:
            self.assertIn("ERP is not reachable right now", self.profile_text())
        find_customer.assert_not_called()  # no slow retries when the ERP is down

    def test_no_email(self):
        self.user.email = ""
        self.user.save()
        self.assertEqual(erp_link_status(self.user)[:21], "Add your email addres")
