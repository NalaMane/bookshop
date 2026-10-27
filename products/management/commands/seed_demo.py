"""Fill the database with demo data for testing and the presentation:
    python manage.py seed_demo

Creates: 10 books (with ERP ID = ISBN and stock, see seed_books), a staff account,
a customer account and 3 sample orders.
Safe to run more than once (nothing is duplicated).
"""
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand

from orders.models import Order, OrderItem
from products.models import Product

PASSWORD = "demo12345"


class Command(BaseCommand):
    help = "Add demo books, users and orders"

    def handle(self, *args, **options):
        call_command("seed_books")

        staff, created = User.objects.get_or_create(
            username="staff",
            defaults={"first_name": "Shop", "last_name": "Admin", "email": "staff@bookshop.test",
                      "is_staff": True, "is_superuser": True},
        )
        if created:
            staff.set_password(PASSWORD)
            staff.save()

        customer, created = User.objects.get_or_create(
            username="anna",
            defaults={"first_name": "Anna", "last_name": "Muster", "email": "anna@bookshop.test"},
        )
        if created:
            customer.set_password(PASSWORD)
            customer.save()
            customer.profile.address = "Bayernallee 11\n52066 Aachen"
            customer.profile.save()

        if not customer.orders.exists():
            sample_orders = [
                (Order.Status.COMPLETED, [("Dune", 1), ("The Hobbit", 2)]),
                (Order.Status.SHIPPED, [("Clean Code", 1)]),
                (Order.Status.PENDING, [("Atomic Habits", 1), ("1984", 1)]),
            ]
            for status, lines in sample_orders:
                order = Order.objects.create(
                    customer=customer, status=status, shipping_address=customer.profile.address
                )
                for name, quantity in lines:
                    book = Product.objects.filter(name=name).exclude(stock__isnull=True).first()
                    if book is None:
                        continue
                    OrderItem.objects.create(
                        order=order, product=book, product_name=book.name,
                        unit_price=book.price, quantity=quantity,
                    )
                order.recalculate_total()

        self.stdout.write(self.style.SUCCESS(
            f"Demo data ready. Logins (password '{PASSWORD}'): staff (admin), anna (customer)"
        ))