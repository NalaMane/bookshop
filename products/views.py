"""Products app - owner: Svenja.

Basic working versions are here so the site runs. Improve freely:
search, styling, pagination, nicer forms, etc.
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProductForm
from .models import Product  
from orders.cart import Cart
"""connects to the model in models.py"""


def product_list(request):
    products = Product.objects.all()
    query = request.GET.get("q")
    products = products.filter(name__icontains=query) if query else products
    print(query)
    cart = Cart(request)

    for product in products:
        key = str(product.pk)
        product.quantity = cart.data.get(key, 0)

    return render(request, "products/product_list.html", {"products": products, "cart": cart})


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, "products/product_detail.html", {"product": product})


@staff_member_required
def product_create(request):
    form = ProductForm(request.POST or None)
    if form.is_valid():
        product = form.save()
        return redirect("products:detail", pk=product.pk)
    return render(request, "products/product_form.html", {"form": form, "title": "Add book"})


@staff_member_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if form.is_valid():
        form.save()
        return redirect("products:detail", pk=product.pk)
    return render(request, "products/product_form.html", {"form": form, "title": "Edit book"})


@staff_member_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        product.delete()
        return redirect("products:list")
    return render(request, "products/product_confirm_delete.html", {"product": product})
