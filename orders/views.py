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

from accounts.erp_customers import erp_customer_for
from bookshop import erp_client as erp

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

        try:
            erp_customer = erp_customer_for(request.user)
            erp_order_id = erp.create_order(
                erp_customer.id,
                [(item["product"].erp_id, item["quantity"]) for item in items],
            )
        except erp.InsufficientStock as error:
            messages.error(request, error.message)
            return redirect("orders:cart")
        except erp.ERPUnavailable:
            messages.error(request, "Orders cannot be placed right now. Please try again later.")
            return redirect("orders:cart")
        except erp.ERPBusinessError as error:
            messages.error(request, error.message)
            return redirect("orders:cart")
        except erp.ERPConfigError:
            messages.error(request, "The ERP is not configured correctly. Please try again later.")
            return redirect("orders:cart")

        with transaction.atomic():
            order = Order.objects.create(
                customer=request.user,
                shipping_address=shipping_address,
                erp_order_id=erp_order_id,
            )
            for item in items:
                product = item["product"]
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    unit_price=product.price,
                    quantity=item["quantity"],
                )
            order.recalculate_total()
        cart.clear()
        messages.success(request, f"Thank you! Your order was placed (ERP order #{erp_order_id}).")
        return redirect("orders:detail", pk=order.pk)

    return render(request, "orders/checkout.html", {"items": items, "total": cart.total()})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    return render(request, "orders/order_detail.html", {"order": order})
