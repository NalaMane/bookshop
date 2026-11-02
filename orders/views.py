"""Cart & orders app - owner: Agasi.

Basic working cart (add / +/- quantity / remove) and checkout.
Order status is changed by staff in /admin (Orders list). Improve freely.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from products.models import Product

from .cart import Cart
from .models import Order, OrderItem


def _is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _cart_json(request, message, *, error=False):
    return JsonResponse(
        {
            "success": not error,
            "message": message,
            "cart_count": len(Cart(request)),
        },
        status=400 if error else 200,
    )


def _cart_totals(request):
    cart = Cart(request)
    return cart, cart.total()


def cart_detail(request):
    cart = Cart(request)
    return render(request, "orders/cart.html", {"items": cart.items(), "total": cart.total()})


@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    try:
        Cart(request).add(product.pk)
    except ValueError as error:
        if _is_ajax(request):
            return _cart_json(request, str(error), error=True)
        messages.error(request, str(error))
        return redirect(request.META.get("HTTP_REFERER", "orders:cart"))  # stay on the same page
    if _is_ajax(request):
        return JsonResponse(
            {
                "success": True,
                "message": f'"{product.name}" added to cart.',
                "cart_count": len(Cart(request)),
                "quantity": Cart(request).data[str(product.pk)],
                "stock": product.stock,
            }
        )
    messages.success(request, f'"{product.name}" added to cart.')
    return redirect(request.META.get("HTTP_REFERER", "orders:cart"))


@require_POST
def cart_update(request, product_id):
    """Set the quantity. Template sends quantity = current +/- 1. 0 removes the item."""
    raw_quantity = request.POST.get("quantity", "")
    try:
        quantity = int(raw_quantity)
    except (TypeError, ValueError):
        if _is_ajax(request):
            return _cart_json(request, "Please enter a valid quantity.", error=True)
        messages.error(request, "Please enter a valid quantity.")
        return redirect("orders:cart")

    if quantity < 0:
        if _is_ajax(request):
            return _cart_json(request, "Quantity cannot be negative.", error=True)
        messages.error(request, "Quantity cannot be negative.")
        return redirect("orders:cart")

    try:
        Cart(request).set(product_id, quantity)
    except ValueError as error:
        if _is_ajax(request):
            return _cart_json(request, str(error), error=True)
        messages.error(request, str(error))
        return redirect("orders:cart")
    if _is_ajax(request):
        cart, total = _cart_totals(request)
        product = get_object_or_404(Product, pk=product_id)
        return JsonResponse(
            {
                "success": True,
                "message": "Basket updated.",
                "cart_count": len(Cart(request)),
                "quantity": Cart(request).data.get(str(product.pk), 0),
                "stock": product.stock,
                "subtotal": str(product.price * Cart(request).data.get(str(product.pk), 0)),
                "total": str(total),
            }
        )
    messages.success(request, "Basket updated.")
    # return redirect("orders:cart")
    return redirect(request.META.get("HTTP_REFERER", "orders:cart"))


@require_POST
def cart_remove(request, product_id):
    Cart(request).remove(product_id)
    if _is_ajax(request):
        _, total = _cart_totals(request)
        return JsonResponse(
            {
                "success": True,
                "message": "Item removed from your basket.",
                "cart_count": len(Cart(request)),
                "removed": True,
                "total": str(total),
            }
        )
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
