"""Template context processors for the home app."""


def cart_count(request):
    """Total number of units in the session cart, available to every template
    (used for the navbar badge)."""
    cart = request.session.get('cart', {})
    return {'cart_count': sum(cart.values())}
