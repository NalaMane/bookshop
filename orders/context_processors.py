from .cart import Cart


def cart_count(request):
    """Makes {{ cart_count }} available in every template (used in the navbar)."""
    return {"cart_count": len(Cart(request))}
