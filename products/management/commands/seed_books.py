"""Fill the database with sample books: python manage.py seed_books"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from products.models import Product

BOOKS = [
    ("Pride and Prejudice", "Jane Austen", "A classic novel of manners and marriage.", "9.99"),
    ("1984", "George Orwell", "A dystopian story about surveillance and control.", "12.50"),
    ("The Hobbit", "J.R.R. Tolkien", "Bilbo Baggins sets off on an unexpected journey.", "14.90"),
    ("Clean Code", "Robert C. Martin", "A handbook of agile software craftsmanship.", "34.99"),
    ("Sapiens", "Yuval Noah Harari", "A brief history of humankind.", "18.00"),
    ("The Little Prince", "Antoine de Saint-Exupéry", "A poetic tale about love and loss.", "7.95"),
    ("Dune", "Frank Herbert", "Politics and survival on the desert planet Arrakis.", "16.99"),
    ("Atomic Habits", "James Clear", "Small changes, remarkable results.", "19.90"),
    ("Crime and Punishment", "Fyodor Dostoevsky", "A student's crime and its consequences.", "11.50"),
    ("Python Crash Course", "Eric Matthes", "A hands-on introduction to programming.", "29.99"),
]


class Command(BaseCommand):
    help = "Add sample books (skips books that already exist)"

    def handle(self, *args, **options):
        created = 0
        for name, author, description, price in BOOKS:
            _, was_created = Product.objects.get_or_create(
                name=name,
                defaults={"author": author, "description": description, "price": Decimal(price)},
            )
            created += was_created
        self.stdout.write(self.style.SUCCESS(f"Added {created} books."))
