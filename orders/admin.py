from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "created_at", "status", "total_price")
    list_filter = ("status",)
    list_editable = ("status",)  # staff can change status straight from the list
    inlines = [OrderItemInline]
