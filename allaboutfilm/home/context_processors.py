"""Template context processors for the home app."""

from .models import WishlistItem


def cart_count(request):
    """Total number of units in the session cart, available to every template
    (used for the navbar badge)."""
    cart = request.session.get('cart', {})
    return {'cart_count': sum(cart.values())}


def wishlist_codes(request):
    """Set of product codes in the current user's wishlist, so product cards
    can render the correct heart state anywhere they appear."""
    if request.user.is_authenticated:
        return {'wishlist_codes': set(
            WishlistItem.objects.filter(user=request.user).values_list('product_id', flat=True)
        )}
    return {'wishlist_codes': set()}
