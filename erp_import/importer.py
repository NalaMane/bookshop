"""Lab 2 – saves the validated ERP rows in the shop (owner: Svenja).

For every row from read_and_validate():
  1. a product with this erp_id exists          -> update it
  2. otherwise: exactly ONE product without erp_id has the same name (old book added
     in the shop) -> link it (set erp_id) and update it, so no duplicate is created
  3. otherwise                                   -> create a new product

The ERP is the master for name, price and stock. Shop-only data (author, cover) is never
overwritten, and the description is only replaced when the ERP sends one.
Content Enricher: if the ERP product ID is an ISBN and the book has no cover yet,
the cover link is added from Open Library.
Everything runs in one transaction: if something fails, nothing of this file is saved.
"""
import re

from django.db import transaction
from django.db.models import Q

from products.models import Product

COVER_URL = "https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"
ISBN = re.compile(r"^(97[89]\d{10}|\d{9}[\dX])$")  # ISBN-13 or ISBN-10


def isbn_from(erp_id):
    """'978-0-547-92822-7' -> '9780547928227'; None if the ID is not an ISBN."""
    digits = re.sub(r"[\s-]", "", erp_id or "").upper()
    return digits if ISBN.match(digits) else None


def find_product(row):
    """Return (product or None, linked?) – see steps 1 and 2 above."""
    product = Product.objects.filter(erp_id=row["erp_id"]).first()
    if product:
        return product, False
    wanted = normalize(row["name"])
    same_name = [book for book in Product.objects.filter(Q(erp_id__isnull=True) | Q(erp_id=""))
                 if normalize(book.name) == wanted]
    if len(same_name) == 1:  # only link if it's clear which book is meant
        return same_name[0], True
    return None, False


def normalize(name):
    """'  The  Hobbit ' -> 'the hobbit' (ignore upper/lower case and extra spaces)."""
    return " ".join((name or "").split()).lower()


@transaction.atomic
def import_rows(rows):
    created = 0
    updated = 0

    for row in rows:
        product, _linked = find_product(row)
        if product is None:
            product = Product(erp_id=row["erp_id"])
            created += 1
        else:
            product.erp_id = row["erp_id"]
            updated += 1

        product.name = row["name"]
        product.price = row["price"]
        product.stock = row["stock"]
        if row["description"]:
            product.description = row["description"]
        isbn = isbn_from(row["erp_id"])
        if isbn and not product.cover_url:
            product.cover_url = COVER_URL.format(isbn=isbn)
        product.save()

    return created, updated
