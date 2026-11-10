"""Lab 3 – live stock from the ERP for the product pages (owner: Svenja).

The ERP is the single source of truth for stock. The shop does NOT use its own
`Product.stock` field anymore – it asks the ERP (via bookshop/erp_client.py).

To keep pages fast, the answer is cached for a few seconds (STOCK_CACHE_SECONDS).
Checkout never uses this cache – there the ERP checks the stock itself (createOrder).
"""
import logging

from django.core.cache import cache

from bookshop import erp_client as erp

logger = logging.getLogger(__name__)

STOCK_CACHE_KEY = "erp_stock_map"
STOCK_CACHE_SECONDS = 15  # short: stock shown is at most 15 s old


def get_stock_map():
    """{isbn: stock} for all ERP books, or None if the ERP is unavailable.

    1. Look in the cache -> found: return it (no ERP call).
    2. Not found -> ask the ERP once for ALL books, store the answer for 15 s.
    3. ERP down / error -> return None (the page shows "unavailable").
    """
    stock_map = cache.get(STOCK_CACHE_KEY)
    if stock_map is not None:
        return stock_map

    try:
        stock_map = erp.get_stock_map()
    except erp.ERPError as error:
        logger.warning("Stock information unavailable: %s", error)
        return None  # not cached, so the next page view tries the ERP again

    cache.set(STOCK_CACHE_KEY, stock_map, STOCK_CACHE_SECONDS)
    return stock_map


def add_live_stock(products):
    """Attach the ERP stock to each product as `product.live_stock`.

    live_stock = 5     -> in stock (5 left)
    live_stock = 0     -> out of stock, or the book is not in the ERP
    live_stock = None  -> ERP unavailable, we don't know

    Returns True if the ERP answered, False if it was unavailable.
    """
    stock_map = get_stock_map()
    for product in products:
        if stock_map is None:
            product.live_stock = None
        else:
            # erp_id is the ISBN = productID in the ERP. Not in the ERP -> 0 (can't be bought).
            product.live_stock = stock_map.get(product.erp_id, 0)
    return stock_map is not None
