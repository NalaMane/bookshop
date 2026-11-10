"""Lab 3 – automatic book catalog sync from the ERP API (owner: Ami).

Lab 2 brought books into the shop with a file (export + upload by hand).
Here the shop loads the book list directly from the ERP via RPC
(erp.get_products()) – no file, no clicking:

  * book with this ISBN (erp_id) already in the shop -> name / price / description updated
  * new ISBN in the ERP                               -> book created (cover from the ISBN)
  * stock is NOT copied – it is always read live from the ERP (products/stock.py)
  * books are never deleted automatically (old orders point to them)

When does it run?
  * automatically when someone opens the book list, at most once every
    ERP_CATALOG_SYNC_SECONDS (default 60 s) – so new ERP books appear by themselves
  * by hand or from a scheduler:  python manage.py sync_products
"""
import logging

from django.conf import settings
from django.core.cache import cache
from django.db import transaction

from bookshop import erp_client as erp
from erp_import.importer import COVER_URL, isbn_from

from .models import Product

logger = logging.getLogger(__name__)

LAST_SYNC_KEY = "erp_catalog_last_sync"


@transaction.atomic
def sync_catalog(erp_products=None):
    """Create / update shop books from the ERP. Returns (created, updated).
    Raises erp.ERPError if the ERP can't be asked."""
    if erp_products is None:
        erp_products = erp.get_products()

    existing = {p.erp_id: p for p in Product.objects.exclude(erp_id__isnull=True).exclude(erp_id="")}
    created = updated = 0
    for item in erp_products:
        erp_id = (item.get("productID") or "").strip()
        name = (item.get("name") or "").strip()
        if not erp_id or not name or item.get("price") is None:
            logger.warning("ERP product skipped (ID, name or price missing): %r", item)
            continue

        product = existing.get(erp_id)
        is_new = product is None
        if is_new:
            product = Product(erp_id=erp_id)

        changed = is_new
        for field, value in (("name", name[:200]), ("price", item["price"])):
            if getattr(product, field) != value:
                setattr(product, field, value)
                changed = True
        description = (item.get("description") or "").strip()
        if description and product.description != description:  # keep the shop's text if the ERP has none
            product.description = description
            changed = True
        isbn = isbn_from(erp_id)
        if isbn and not product.cover_url:  # Content Enricher, same as Lab 2
            product.cover_url = COVER_URL.format(isbn=isbn)
            changed = True

        if changed:  # only write to the database when something really changed
            product.save()
            created += is_new
            updated += not is_new

    if created or updated:
        logger.info("ERP catalog sync: %s created, %s updated.", created, updated)
    return created, updated


def sync_catalog_if_due():
    """Called by the book list page. Syncs at most once per ERP_CATALOG_SYNC_SECONDS.
    Never raises: if the ERP is down, the page just shows the books we already have."""
    seconds = settings.ERP_CATALOG_SYNC_SECONDS
    if seconds <= 0:
        return None  # switched off (e.g. in the tests)
    if not cache.add(LAST_SYNC_KEY, True, seconds):
        return None  # synced recently (or another request is syncing right now)
    try:
        return sync_catalog()
    except erp.ERPError as error:
        # The key stays set, so a down ERP is only tried again after `seconds`
        # – the page doesn't wait for the retries on every visit.
        logger.warning("ERP catalog sync failed: %s", error)
        return None
