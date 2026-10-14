"""Accounts app - owner: Ami.

Basic working versions of register / login / logout / profile / purchase history.
Improve freely: validation messages, styling, password change, etc.
"""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import AddressForm, RegisterForm, StyledPasswordChangeForm, UserUpdateForm


def register(request):
    form = RegisterForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome! Your account was created.")
        return redirect("products:list")
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    user_form = UserUpdateForm(request.POST or None, instance=request.user)
    address_form = AddressForm(request.POST or None, initial={"address": request.user.profile.address})
    if request.method == "POST" and user_form.is_valid() and address_form.is_valid():
        user_form.save()
        request.user.profile.address = address_form.cleaned_data["address"]
        request.user.profile.save()
        messages.success(request, "Profile updated.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"user_form": user_form, "address_form": address_form})


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
