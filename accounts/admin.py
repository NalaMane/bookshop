from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.db.models import Count

from .models import Profile


class ProfileInline(admin.StackedInline):
    """Shows the customer's address directly on the user page in /admin."""

    model = Profile
    can_delete = False
    verbose_name_plural = "Customer profile"


class CustomerAdmin(UserAdmin):
    """User admin extended for customer management: address, number of orders, search."""

    inlines = [ProfileInline]
    list_display = ("username", "first_name", "last_name", "email", "address", "order_count", "is_staff")
    search_fields = ("username", "first_name", "last_name", "email",
                     "profile__street", "profile__postal_code", "profile__city")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("profile").annotate(_order_count=Count("orders"))

    @admin.display(description="Address")
    def address(self, user):
        return user.profile.address.replace("\n", ", ") if hasattr(user, "profile") else ""

    @admin.display(description="Orders", ordering="_order_count")
    def order_count(self, user):
        return user._order_count


admin.site.unregister(User)
admin.site.register(User, CustomerAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "street", "postal_code", "city")
    search_fields = ("user__username", "user__email", "street", "postal_code", "city")
