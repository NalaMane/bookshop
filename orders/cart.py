"""Session-based shopping cart. Stored as {"<product_id>": quantity} in the session."""
from decimal import Decimal

from products.models import Product

CART_SESSION_KEY = "cart"
MAX_ITEM_QUANTITY = 99


class Cart:
    def __init__(self, request):
        self.session = request.session
        self.data = self.session.setdefault(CART_SESSION_KEY, {})

    def add(self, product_id, quantity=1):
        key = str(product_id)
        new_quantity = self.data.get(key, 0) + quantity
        if new_quantity < 1 or new_quantity > MAX_ITEM_QUANTITY:
            raise ValueError(f"Quantity must be between 1 and {MAX_ITEM_QUANTITY}.")
        self._validate_stock(product_id, new_quantity)
        self.data[key] = new_quantity
        self._save()

    def set(self, product_id, quantity):
        key = str(product_id)
        if quantity > MAX_ITEM_QUANTITY:
            raise ValueError(f"Quantity cannot exceed {MAX_ITEM_QUANTITY}.")
        if quantity > 0:
            self._validate_stock(product_id, quantity)
            self.data[key] = quantity
        else:
            self.data.pop(key, None)
        self._save()

    def remove(self, product_id):
        self.data.pop(str(product_id), None)
        self._save()

    def clear(self):
        self.session[CART_SESSION_KEY] = {}
        self.data = self.session[CART_SESSION_KEY]
        self._save()

    def items(self):
        """List of dicts: product, quantity, subtotal."""
        product_ids = {
            product_id
            for product_id, quantity in self.data.items()
            if isinstance(quantity, int) and not isinstance(quantity, bool) and 0 < quantity <= MAX_ITEM_QUANTITY
        }
        products = Product.objects.filter(pk__in=product_ids)
        found_ids = {str(product.pk) for product in products}
        stale_ids = set(self.data) - found_ids
        if stale_ids:
            for product_id in stale_ids:
                self.data.pop(product_id, None)
            self._save()
        return [
            {"product": p, "quantity": self.data[str(p.pk)], "subtotal": p.price * self.data[str(p.pk)]}
            for p in products
        ]

    def total(self):
        return sum((item["subtotal"] for item in self.items()), Decimal("0"))

    def __len__(self):
        return sum(item["quantity"] for item in self.items())

    def _save(self):
        self.session.modified = True

    @staticmethod
    def _validate_stock(product_id, quantity):
        try:
            product = Product.objects.only("stock").get(pk=product_id)
        except Product.DoesNotExist as error:
            raise ValueError("This book is no longer available.") from error
        if product.stock is None:
            raise ValueError("This book is not available for purchase.")
        if quantity > product.stock:
            raise ValueError(
                f"Only {product.stock} of this book are currently in stock."
            )
