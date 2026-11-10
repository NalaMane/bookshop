"""Lab 3 – which ERP customer an order belongs to (owner: Ami).

Every ERP order needs an ERP customer, but the ERP API can't create customers.
So for a shop user we:
  1. look up the ERP customer with the same email (case-insensitive),
  2. if there is none, use the default web shop customer from the settings
     (ERP_DEFAULT_CUSTOMER_ID = Christian Drumm, same ID after every ERP restart).

The ID is NOT stored in the shop database: every one of us runs their own ERP
and it forgets everything on restart, so we always ask the ERP at the moment
of the order.

Usage (checkout, Agasi):
    from accounts.erp_customers import erp_customer_for
    customer = erp_customer_for(request.user)      # may raise erp.ERPError
    erp.create_order(customer.id, [(isbn, qty), ...])
"""
from dataclasses import dataclass

from django.conf import settings

from bookshop import erp_client as erp


@dataclass(frozen=True)
class ERPCustomer:
    id: str  # ERP customer UUID to send with createOrder
    matched: bool  # True = found by email, False = default web shop customer


def erp_customer_for(user):
    """ERP customer for this shop user. Raises erp.ERPError if the ERP can't be asked."""
    customer_id = erp.find_customer(user.email)
    if customer_id:
        return ERPCustomer(customer_id, matched=True)
    return ERPCustomer(settings.ERP_DEFAULT_CUSTOMER_ID, matched=False)


def erp_link_status(user):
    """Short text for the profile page – never raises, the page must work without the ERP."""
    if not user.email:
        return "Add your email address so your orders can be linked to your ERP customer account."
    if not erp.is_available():  # one quick call, no retries – the page must stay fast
        return "The ERP is not reachable right now, so we can't check your ERP customer account."
    try:
        customer = erp_customer_for(user)
    except erp.ERPError:
        return "The ERP is not reachable right now, so we can't check your ERP customer account."
    if customer.matched:
        return "Your account is linked to your customer account in our ERP (same email)."
    return ("Your email is not registered in our ERP yet, so your orders are booked "
            "to our general web shop customer. They still appear in your purchase history.")
