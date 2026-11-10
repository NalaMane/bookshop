"""Products app - owner: Svenja.

Basic working versions are here so the site runs. 
search, styling, pagination, nicer forms, etc.
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProductForm
from .models import Product  
from orders.cart import Cart

from .catalog import sync_catalog_if_due  # Lab 3: book list from the ERP API
from .stock import add_live_stock  # Lab 3: live stock from the ERP
"""connects to the model in models.py"""


def product_list(request):
    sync_catalog_if_due()  # new ERP books appear automatically (at most once a minute)
    products = Product.objects.all()
    query = request.GET.get("q")
    products = products.filter(name__icontains=query) if query else products
    cart = Cart(request)

    products = list(products)  # evaluate once, so live_stock stays on these objects
    for product in products:
        key = str(product.pk)
        product.quantity = cart.data.get(key, 0)
    stock_available = add_live_stock(products)  # ONE ERP call (or cache) for the whole page

    return render(
        request,
        "products/product_list.html",
        {"products": products, "cart": cart, "stock_available": stock_available},
    )


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    cart = Cart(request)
    product.quantity = cart.data.get(str(product.pk), 0)
    stock_available = add_live_stock([product])
    return render(
        request,
        "products/product_detail.html",
        {"product": product, "stock_available": stock_available},
    )


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
