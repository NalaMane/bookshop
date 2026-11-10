"""Lab 3 – the ONE module that talks to the Mini-ERP (owner: Nala).

The ERP (SAP CAP, `cds watch`) is the single source of truth for stock and
orders. The rest of the shop never calls the ERP directly – it only uses the
functions below:

    from bookshop import erp_client as erp

    erp.get_products()                 # all ERP products (list of dicts)
    erp.get_stock("9780547928227")     # -> 24, or None if the ERP doesn't know the ISBN
    erp.get_stock_map()                # -> {"9780547928227": 24, ...}  (one call for a list page)
    erp.find_customer("a@b.de")        # -> ERP customer UUID, or None
    erp.create_order(customer_id, [("9780547928227", 2)])   # -> ERP order ID (int)

ERP REST API: <ERP_API_URL>/products(), /customers(), /orders(), POST /createOrder
Login: Basic Auth with the technical user (role "system-integration").
URL, user, password, timeout and retries come from settings.py / .env.

Errors – catch these in your views:
    ERPUnavailable      ERP down / too slow / 5xx, even after retries  -> "please try again later"
    InsufficientStock   409 from the ERP, e.g. "3 exceeds stock for product #…" -> show .message
    ERPBusinessError    other "no" from the ERP (422, unknown ISBN …)  -> show .message
    ERPConfigError      401/403/404: wrong URL or login – a setup problem, logged as error
All of them inherit from ERPError, so `except erp.ERPError` catches everything.

Retry rules: only technical errors are retried (connection error, timeout, 5xx),
with a short pause (0.5 s, 1 s, …). A business "no" (409/422) or a login error
is never retried – asking again won't change the answer.
createOrder is special: a retry could create the order twice, so before
retrying we look in orders() whether the first try already got through.
"""
import logging
import time
from datetime import date
from decimal import Decimal

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# One session = re-uses the TCP connection to the ERP (faster than a new one per call).
_session = requests.Session()


# --------------------------------------------------------------------------- errors


class ERPError(Exception):
    """Base class for every ERP problem."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.message = message
        self.status = status


class ERPUnavailable(ERPError):
    """ERP not reachable, timed out or returned 5xx – even after all retries."""


class ERPConfigError(ERPError):
    """401/403/404 – wrong URL, user or password in the settings/.env."""


class ERPBusinessError(ERPError):
    """The ERP understood the request and said no (e.g. 422)."""


class InsufficientStock(ERPBusinessError):
    """409 – not enough stock for at least one product."""


# --------------------------------------------------------------------------- low level


def _url(function):
    return f"{settings.ERP_API_URL.rstrip('/')}/{function}"


def _error_message(response):
    """CAP sends errors as {"error": {"code": "409", "message": "..."}}."""
    try:
        return response.json()["error"]["message"]
    except (ValueError, KeyError, TypeError):
        return response.text[:300] or f"HTTP {response.status_code}"


def _raise_for_status(response):
    status = response.status_code
    if status < 400:
        return
    message = _error_message(response)
    if status in (401, 403, 404):
        logger.error("ERP config problem (%s) for %s: %s", status, response.url, message)
        raise ERPConfigError(
            f"ERP rejected the request ({status}) – check ERP_API_URL / ERP_USER / ERP_PASSWORD.",
            status,
        )
    if status == 409:
        raise InsufficientStock(message, status)
    raise ERPBusinessError(message, status)


def _send(method, function, payload=None):
    """One HTTP call, no retry. Technical problems become ERPUnavailable."""
    try:
        response = _session.request(
            method,
            _url(function),
            json=payload,
            auth=(settings.ERP_USER, settings.ERP_PASSWORD),
            timeout=settings.ERP_TIMEOUT,
        )
    except requests.Timeout as error:
        raise ERPUnavailable(f"ERP did not answer within {settings.ERP_TIMEOUT} s.") from error
    except requests.ConnectionError as error:
        raise ERPUnavailable("ERP is not reachable (is `cds watch` running?).") from error
    if response.status_code >= 500:
        raise ERPUnavailable(f"ERP error {response.status_code}: {_error_message(response)}", response.status_code)
    _raise_for_status(response)
    return response


def _pause(attempt):
    """0.5 s, 1 s, 2 s … between tries."""
    time.sleep(settings.ERP_RETRY_DELAY * (2 ** (attempt - 1)))


def _call(method, function, payload=None):
    """HTTP call with retries for technical errors only. Returns parsed JSON (or None)."""
    attempts = max(1, settings.ERP_RETRIES)
    for attempt in range(1, attempts + 1):
        try:
            response = _send(method, function, payload)
            return response.json() if response.content else None
        except ERPUnavailable as error:
            logger.warning("ERP %s %s failed (try %s/%s): %s", method, function, attempt, attempts, error)
            if attempt == attempts:
                raise
            _pause(attempt)


# --------------------------------------------------------------------------- products & stock


def get_products():
    """All ERP products: [{"ID": uuid, "productID": isbn, "name", "price": Decimal, "currency", "stock": int}, …]"""
    products = _call("GET", "products()") or []
    for product in products:
        if product.get("price") is not None:
            product["price"] = Decimal(str(product["price"]))
    return products


def get_product(isbn):
    """One ERP product by ISBN (the ERP's productID), or None. The ERP has no single-product call."""
    isbn = str(isbn).strip()
    return next((p for p in get_products() if p.get("productID") == isbn), None)


def get_stock(isbn):
    """Current stock for one ISBN, or None if the ERP doesn't know this book."""
    product = get_product(isbn)
    return None if product is None else int(product.get("stock") or 0)


def get_stock_map():
    """{isbn: stock} for all ERP products – one ERP call for a whole list page."""
    return {p["productID"]: int(p.get("stock") or 0) for p in get_products()}


# --------------------------------------------------------------------------- customers


def get_customers():
    """All ERP customers: [{"customerID": uuid, "name", "email", …}]"""
    return _call("GET", "customers()") or []


def find_customer(email):
    """ERP customer UUID for this email (case-insensitive), or None.
    The ERP API can't create customers – fall back to settings.ERP_DEFAULT_CUSTOMER_ID."""
    email = (email or "").strip().lower()
    if not email:
        return None
    for customer in get_customers():
        if (customer.get("email") or "").strip().lower() == email:
            return customer["customerID"]
    return None


# --------------------------------------------------------------------------- orders


def get_orders():
    """All ERP orders: [{"orderID": int, "customer": uuid, "orderDate", "orderAmount", "orderStatus", "items": […]}]"""
    return _call("GET", "orders()") or []


def _max_order_id():
    return max((o.get("orderID") or 0 for o in get_orders()), default=0)


def _find_new_order(after_id, customer_id, amount):
    """The order we just created: newer than after_id, same customer and amount."""
    matches = [
        o
        for o in get_orders()
        if (o.get("orderID") or 0) > after_id
        and o.get("customer") == customer_id
        and Decimal(str(o.get("orderAmount") or 0)) == amount
    ]
    return max(matches, key=lambda o: o["orderID"])["orderID"] if matches else None


def create_order(customer_id, items, currency="EUR"):
    """Create a purchase order in the ERP and return its ERP order ID.

    customer_id: ERP customer UUID (see find_customer / settings.ERP_DEFAULT_CUSTOMER_ID)
    items:       [(isbn, quantity), …]

    ISBNs are mapped to the ERP's internal product UUIDs and prices are taken
    from the ERP right now (the ERP is the source of truth). The ERP checks the
    stock and reduces it itself.

    Raises InsufficientStock (409), ERPBusinessError (unknown ISBN, 422),
    ERPUnavailable, ERPConfigError.
    """
    if not items:
        raise ERPBusinessError("An order must contain at least one book.")

    products = {p["productID"]: p for p in get_products()}
    order_items = []
    for isbn, quantity in items:
        product = products.get(str(isbn).strip())
        if product is None:
            raise ERPBusinessError(f"Book {isbn} is not available in the ERP.")
        if int(quantity) < 1:
            raise ERPBusinessError("Quantity must be at least 1.")
        line_amount = (product["price"] * int(quantity)).quantize(Decimal("0.01"))
        order_items.append(
            {
                "product": product["ID"],
                "quantity": int(quantity),
                "itemAmount": float(line_amount),
                "currency": currency,
            }
        )
    total = sum((Decimal(str(i["itemAmount"])) for i in order_items), Decimal("0")).quantize(Decimal("0.01"))

    payload = {
        "order": {
            "customer": customer_id,
            "orderDate": date.today().isoformat(),
            "orderAmount": float(total),
            "currency": currency,
            "items": order_items,
        }
    }

    # createOrder returns nothing, so remember the highest order ID before,
    # then find the new order afterwards. Same trick protects the retries.
    before_id = _max_order_id()
    attempts = max(1, settings.ERP_RETRIES)
    for attempt in range(1, attempts + 1):
        try:
            _send("POST", "createOrder", payload)
            break
        except ERPUnavailable as error:
            logger.warning("ERP createOrder failed (try %s/%s): %s", attempt, attempts, error)
            # Maybe the ERP saved the order but the answer got lost – don't order twice.
            try:
                existing = _find_new_order(before_id, customer_id, total)
            except ERPUnavailable:
                existing = None
            if existing is not None:
                logger.info("ERP order %s was created despite the error – not retrying.", existing)
                return existing
            if attempt == attempts:
                raise
            _pause(attempt)

    order_id = _find_new_order(before_id, customer_id, total)
    if order_id is None:
        # Shouldn't happen: the ERP said OK but we can't see the order.
        raise ERPUnavailable("ERP accepted the order but it could not be found in orders().")
    logger.info("ERP order %s created for customer %s (%s %s).", order_id, customer_id, total, currency)
    return order_id


# --------------------------------------------------------------------------- health


def is_available():
    """True if the ERP answers right now (single quick call, no retries)."""
    try:
        _send("GET", "customers()")
        return True
    except ERPError:
        return False
