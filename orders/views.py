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
    try:
        Cart(request).add(product.pk)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("orders:cart")
    messages.success(request, f'"{product.name}" added to cart.')
    return redirect(request.META.get("HTTP_REFERER", "orders:cart"))


@require_POST
def cart_update(request, product_id):
    """Set the quantity. Template sends quantity = current +/- 1. 0 removes the item."""
    raw_quantity = request.POST.get("quantity", "")
    try:
        quantity = int(raw_quantity)
    except (TypeError, ValueError):
        messages.error(request, "Please enter a valid quantity.")
        return redirect("orders:cart")

    if quantity < 0:
        messages.error(request, "Quantity cannot be negative.")
        return redirect("orders:cart")

    try:
        Cart(request).set(product_id, quantity)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("orders:cart")
    messages.success(request, "Basket updated.")
    # return redirect("orders:cart")
    return redirect(request.META.get("HTTP_REFERER", "orders:cart"))


@require_POST
def cart_remove(request, product_id):
    Cart(request).remove(product_id)
    messages.success(request, "Item removed from your basket.")
    return redirect("orders:cart")


@login_required
def checkout(request):
    cart = Cart(request)
    items = cart.items()
    if not items:
        messages.warning(request, "Your cart is empty.")
        return redirect("orders:cart")

    if request.method == "POST":
        shipping_address = request.user.profile.address.strip()
        if not shipping_address:
            messages.error(request, "Please add a shipping address to your profile before ordering.")
            return redirect("accounts:profile")

        with transaction.atomic():
            locked_products = {
                product.pk: product
                for product in Product.objects.select_for_update().filter(
                    pk__in=[item["product"].pk for item in items]
                )
            }
            for item in items:
                product = locked_products.get(item["product"].pk)
                if product is None:
                    messages.error(request, "A book in your cart is no longer available.")
                    return redirect("orders:cart")
                if product.stock is None:
                    messages.error(
                        request,
                        f'"{product.name}" is no longer available for purchase.',
                    )
                    return redirect("orders:cart")
                if item["quantity"] > product.stock:
                    messages.error(
                        request,
                        f'Only {product.stock} of "{product.name}" are currently in stock.',
                    )
                    return redirect("orders:cart")

            order = Order.objects.create(
                customer=request.user,
                shipping_address=shipping_address,
            )
            for item in items:
                product = locked_products[item["product"].pk]
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    unit_price=product.price,
                    quantity=item["quantity"],
                )
                product.stock -= item["quantity"]
                product.save(update_fields=["stock"])
            order.recalculate_total()
        cart.clear()
        messages.success(request, "Thank you! Your order was placed.")
        return redirect("products:list")

    return render(request, "orders/checkout.html", {"items": items, "total": cart.total()})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    return render(request, "orders/order_detail.html", {"order": order})
