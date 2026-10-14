"""Cart & orders app - owner: Agasi.

Basic working cart (add / +/- quantity / remove) and checkout.
Order status is changed by staff in /admin (Orders list). Improve freely.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from products.models import Product

from .cart import Cart
from .models import Order, OrderItem


def cart_detail(request):
    cart = Cart(request)
    return render(request, "orders/cart.html", {"items": cart.items(), "total": cart.total()})


@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    Cart(request).add(product.pk)
    messages.success(request, f'"{product.name}" added to cart.')
    return redirect(request.META.get("HTTP_REFERER", "orders:cart"))


@require_POST
def cart_update(request, product_id):
    """Set the quantity. Template sends quantity = current +/- 1. 0 removes the item."""
    quantity = int(request.POST.get("quantity", 1))
    Cart(request).set(product_id, quantity)
    return redirect("orders:cart")


@require_POST
def cart_remove(request, product_id):
    Cart(request).remove(product_id)
    return redirect("orders:cart")


@login_required
def checkout(request):
    cart = Cart(request)
    items = cart.items()
    if not items:
        messages.warning(request, "Your cart is empty.")
        return redirect("orders:cart")

    if request.method == "POST":
        with transaction.atomic():
            order = Order.objects.create(
                customer=request.user,
                shipping_address=request.user.profile.address,
            )
            for item in items:
                OrderItem.objects.create(
                    order=order,
                    product=item["product"],
                    product_name=item["product"].name,
                    unit_price=item["product"].price,
                    quantity=item["quantity"],
                )
            order.recalculate_total()
        cart.clear()
        messages.success(request, f"Thank you! Order #{order.pk} was placed.")
        return redirect("orders:detail", pk=order.pk)

    return render(request, "orders/checkout.html", {"items": items, "total": cart.total()})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    return render(request, "orders/order_detail.html", {"order": order})
