"""Main URL config (owner: Nala). Each app has its own urls.py - add routes there, not here."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),  # Ami
    path("orders/", include("orders.urls")),  # Agasi
    path("erp/", include("erp_import.urls")),  # Lab 2
    path("", include("products.urls")),  # Svenja (homepage = book list)
]
