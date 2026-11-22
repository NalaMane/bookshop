"""Accounts app - owner: Ami.

Basic working versions of register / login / logout / profile / purchase history.
Improve freely: validation messages, styling, password change, etc.
"""
from django.contrib import messages
import json

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.core import signing
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from orders.cart import (
    CART_SESSION_KEY,
    PRESERVED_CART_COOKIE,
    PRESERVED_CART_COOKIE_SALT,
)

from .erp_customers import erp_link_status
from .forms import AddressForm, RegisterForm, StyledPasswordChangeForm, UserUpdateForm


class PreservingLoginView(LoginView):
    def form_valid(self, form):
        cart = dict(self.request.session.get(CART_SESSION_KEY, {}))
        if not cart:
            try:
                preserved_json = self.request.get_signed_cookie(
                    PRESERVED_CART_COOKIE,
                    salt=PRESERVED_CART_COOKIE_SALT,
                )
                preserved = json.loads(preserved_json)
            except (KeyError, signing.BadSignature, json.JSONDecodeError, TypeError):
                cart = {}
            else:
                cart = preserved if isinstance(preserved, dict) else {}
        response = super().form_valid(form)
        self.request.session[CART_SESSION_KEY] = cart
        self.request.session.modified = True
        return response


def register(request):
    form = RegisterForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome! Your account was created.")
        return redirect("products:list")
    return render(request, "accounts/register.html", {"form": form})


@require_POST
def logout_view(request):
    """Log out without discarding the session-based shopping cart."""
    cart = dict(request.session.get(CART_SESSION_KEY, {}))
    logout(request)
    response = redirect("products:list")
    response.set_signed_cookie(
        PRESERVED_CART_COOKIE,
        json.dumps(cart),
        salt=PRESERVED_CART_COOKIE_SALT,
        max_age=30 * 24 * 60 * 60,
    )
    return response


@login_required
def profile(request):
    user_form = UserUpdateForm(request.POST or None, instance=request.user)
    address_form = AddressForm(request.POST or None, instance=request.user.profile)
    if request.method == "POST" and user_form.is_valid() and address_form.is_valid():
        user_form.save()
        address_form.save()
        messages.success(request, "Profile updated.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {
        "user_form": user_form,
        "address_form": address_form,
        "erp_status": erp_link_status(request.user),  # Lab 3
    })


@login_required
def purchase_history(request):
    orders = request.user.orders.prefetch_related("items")
    return render(request, "accounts/history.html", {"orders": orders})


class PasswordChange(SuccessMessageMixin, PasswordChangeView):
    """Built-in Django view: checks the old password, saves the new one and keeps the user logged in."""

    form_class = StyledPasswordChangeForm
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:profile")
    success_message = "Your password was changed."
