"""Fill the database with sample books: python manage.py seed_books

Also adds a cover image link to sample books that don't have one yet
(covers come from Open Library, looked up by ISBN).
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from products.models import Product

COVER_URL = "https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"

# (title, author, description, price, ISBN for the cover)
BOOKS = [
    ("Pride and Prejudice", "Jane Austen", "A classic novel of manners and marriage.", "9.99", "9780141439518"),
    ("1984", "George Orwell", "A dystopian story about surveillance and control.", "12.50", "9780451524935"),
    ("The Hobbit", "J.R.R. Tolkien", "Bilbo Baggins sets off on an unexpected journey.", "14.90", "9780547928227"),
    ("Clean Code", "Robert C. Martin", "A handbook of agile software craftsmanship.", "34.99", "9780132350884"),
    ("Sapiens", "Yuval Noah Harari", "A brief history of humankind.", "18.00", "9780062316097"),
    ("The Little Prince", "Antoine de Saint-Exupéry", "A poetic tale about love and loss.", "7.95", "9780156012195"),
    ("Dune", "Frank Herbert", "Politics and survival on the desert planet Arrakis.", "16.99", "9780441172719"),
    ("Atomic Habits", "James Clear", "Small changes, remarkable results.", "19.90", "9780735211292"),
    ("Crime and Punishment", "Fyodor Dostoevsky", "A student's crime and its consequences.", "11.50", "9780143058144"),
    ("Python Crash Course", "Eric Matthes", "A hands-on introduction to programming.", "29.99", "9781593279288"),
]


class Command(BaseCommand):
    help = "Add sample books with covers (skips books that already exist)"

    def handle(self, *args, **options):
        created = covers = 0
        for name, author, description, price, isbn in BOOKS:
            cover = COVER_URL.format(isbn=isbn)
            book, was_created = Product.objects.get_or_create(
                name=name,
                defaults={"author": author, "description": description,
                          "price": Decimal(price), "cover_url": cover},
            )
            created += was_created
            if not book.cover_url:  # books added before covers existed
                book.cover_url = cover
                book.save(update_fields=["cover_url"])
                covers += 1
        self.stdout.write(self.style.SUCCESS(f"Added {created} books, added covers to {covers} existing books."))
