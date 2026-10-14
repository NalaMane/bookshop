"""Session-based shopping cart. Stored as {"<product_id>": quantity} in the session."""
from decimal import Decimal

from products.models import Product

CART_SESSION_KEY = "cart"


class Cart:
    def __init__(self, request):
        self.session = request.session
        self.data = self.session.setdefault(CART_SESSION_KEY, {})

    def add(self, product_id, quantity=1):
        key = str(product_id)
        self.data[key] = self.data.get(key, 0) + quantity
        self._save()

    def set(self, product_id, quantity):
        key = str(product_id)
        if quantity > 0:
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
        products = Product.objects.filter(pk__in=self.data.keys())
        return [
            {"product": p, "quantity": self.data[str(p.pk)], "subtotal": p.price * self.data[str(p.pk)]}
            for p in products
        ]

    def total(self):
        return sum((item["subtotal"] for item in self.items()), Decimal("0"))

    def __len__(self):
        return sum(self.data.values())

    def _save(self):
        self.session.modified = True
