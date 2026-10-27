"""Fill the database with sample books: python manage.py seed_books

Lab 2: the ERP is the master system and only books with a stock number can be sold.
So every sample book gets
  * erp_id = its ISBN  -> the same ID the book has in the ERP (enter the ISBN as
                          "Product ID" there), so an ERP import UPDATES these books
                          instead of creating duplicates
  * a stock number      -> the book can be bought
Covers come from Open Library, looked up by the same ISBN.
Existing books are only completed (missing erp_id / stock / cover), never overwritten,
so prices and stock coming from the ERP import are kept.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from products.models import Product

COVER_URL = "https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"

# (title, author, description, price, ISBN = ERP product ID and cover, stock)
BOOKS = [
    ("Pride and Prejudice", "Jane Austen", "A classic novel of manners and marriage.", "9.99", "9780141439518", 20),
    ("1984", "George Orwell", "A dystopian story about surveillance and control.", "12.50", "9780451524935", 25),
    ("The Hobbit", "J.R.R. Tolkien", "Bilbo Baggins sets off on an unexpected journey.", "14.90", "9780547928227", 15),
    ("Clean Code", "Robert C. Martin", "A handbook of agile software craftsmanship.", "34.99", "9780132350884", 8),
    ("Sapiens", "Yuval Noah Harari", "A brief history of humankind.", "18.00", "9780062316097", 12),
    ("The Little Prince", "Antoine de Saint-Exupéry", "A poetic tale about love and loss.", "7.95", "9780156012195", 30),
    ("Dune", "Frank Herbert", "Politics and survival on the desert planet Arrakis.", "16.99", "9780441172719", 10),
    ("Atomic Habits", "James Clear", "Small changes, remarkable results.", "19.90", "9780735211292", 18),
    ("Crime and Punishment", "Fyodor Dostoevsky", "A student's crime and its consequences.", "11.50", "9780143058144", 5),
    ("Python Crash Course", "Eric Matthes", "A hands-on introduction to programming.", "29.99", "9781593279288", 7),
]


class Command(BaseCommand):
    help = "Add sample books with ERP ID (ISBN), stock and cover (existing books are only completed)"

    def handle(self, *args, **options):
        created = completed = 0
        for name, author, description, price, isbn, stock in BOOKS:
            cover = COVER_URL.format(isbn=isbn)
            # 1. already there with this ERP ID (e.g. from an ERP import) -> 2. old book with the
            #    same title but no ERP ID -> link it -> 3. otherwise create it
            book = (Product.objects.filter(erp_id=isbn).first()
                    or Product.objects.filter(name=name, erp_id__isnull=True).first())
            if book is None:
                Product.objects.create(name=name, author=author, description=description,
                                       price=Decimal(price), cover_url=cover, erp_id=isbn, stock=stock)
                created += 1
                continue
            changed = []
            for field, value in (("erp_id", isbn), ("stock", stock), ("cover_url", cover), ("author", author)):
                if getattr(book, field) in (None, ""):  # only fill what is missing
                    setattr(book, field, value)
                    changed.append(field)
            if changed:
                book.save(update_fields=changed)
                completed += 1
        self.stdout.write(self.style.SUCCESS(
            f"Added {created} books, completed {completed} existing books (ERP ID / stock / cover)."))
