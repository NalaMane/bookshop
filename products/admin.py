from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "author", "price", "created_at","erp_id", "stock")
    search_fields = ("name", "author")
