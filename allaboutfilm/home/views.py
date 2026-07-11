from decimal import Decimal

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST

from .forms import ContactForm
from .models import Product, Camera, Lens, Film, ShippingMethod

def home(request):
    return render(request, 'home/welcome.html')

def cameras(request):
    return render(request, 'home/catalog.html', {
        'items': Camera.objects.prefetch_related('images').all(),
        'page_title': 'Cameras',
        'empty_message': 'No cameras available at the moment.',
    })

def lenses(request):
    return render(request, 'home/catalog.html', {
        'items': Lens.objects.prefetch_related('images').all(),
        'page_title': 'Lenses',
        'empty_message': 'No lenses available at the moment.',
    })

def film(request):
    return render(request, 'home/catalog.html', {
        'items': Film.objects.prefetch_related('images').all(),
        'page_title': 'Film',
        'empty_message': 'No film available at the moment.',
    })

def item_detail(request, code):
    product = get_object_or_404(Product, code=code)
    # Resolve the concrete subtype so category-specific fields are available.
    if product.category == Product.Category.CAMERA:
        item, back_url, category_label = product.camera, 'cameras', 'Cameras'
    elif product.category == Product.Category.LENS:
        item, back_url, category_label = product.lens, 'lenses', 'Lenses'
    else:
        item, back_url, category_label = product.film, 'film', 'Film'
    return render(request, 'home/item_detail.html', {
        'item': item,
        'images': item.images.all(),
        'back_url': back_url,
        'category_label': category_label,
    })

def about(request):
    return render(request, 'home/about.html')

def contact(request):
    submitted = False
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # No backend yet - just acknowledge the successful submission
            # and hand a fresh, blank form back to the template.
            form = ContactForm()
            submitted = True
    else:
        form = ContactForm()
    return render(request, 'home/contact.html', {'form': form, 'submitted': submitted})

def account(request):
    return render(request, 'home/account.html')


# ---------------------------------------------------------------------------
# Session-based cart
#
# Auth isn't wired up yet, so the cart lives in the session as {code: quantity}.
# (The DB Cart/CartItem models are reserved for checkout once login exists.)
# ---------------------------------------------------------------------------
def _get_cart(request):
    return request.session.get('cart', {})


def _save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True


def _cart_subtotal(request):
    cart = _get_cart(request)
    subtotal = Decimal('0.00')
    for product in Product.objects.filter(code__in=cart.keys()):
        subtotal += product.price * cart.get(product.code, 0)
    return subtotal


def cart(request):
    cart = _get_cart(request)
    products = Product.objects.filter(code__in=cart.keys()).prefetch_related('images')
    items = []
    subtotal = Decimal('0.00')
    for product in products:
        quantity = cart.get(product.code, 0)
        line_total = product.price * quantity
        subtotal += line_total
        items.append({
            'product': product,
            'quantity': quantity,
            'line_total': line_total,
            'is_film': product.category == Product.Category.FILM,
        })
    return render(request, 'home/cart.html', {
        'items': items,
        'subtotal': subtotal,
        'item_count': sum(cart.values()),
        'shipping_methods': ShippingMethod.objects.filter(is_active=True),
    })


@require_POST
def add_to_cart(request):
    code = request.POST.get('code')
    try:
        quantity = max(1, int(request.POST.get('quantity', 1)))
    except (TypeError, ValueError):
        quantity = 1

    product = get_object_or_404(Product, code=code)
    cart = _get_cart(request)
    current = cart.get(code, 0)
    stock = product.stock

    if current >= stock:
        return JsonResponse({
            'ok': False,
            'cart_count': sum(cart.values()),
            'message': f'Only {stock} in stock — you already have the maximum in your cart.',
        })

    new_total = min(current + quantity, stock)
    cart[code] = new_total
    _save_cart(request, cart)

    if new_total < current + quantity:
        message = f'Only {stock} in stock — added the maximum available.'
    else:
        message = f'{product.manufacturer} {product.model} was added to your cart!'

    return JsonResponse({
        'ok': True,
        'cart_count': sum(cart.values()),
        'message': message,
    })


@require_POST
def update_cart(request):
    code = request.POST.get('code')
    action = request.POST.get('action')
    product = get_object_or_404(Product, code=code)
    cart = _get_cart(request)

    if code not in cart:
        return JsonResponse({'ok': False, 'message': 'Item not in cart.'}, status=404)

    quantity = cart[code]
    ok, message = True, None

    if action == 'inc':
        if quantity < product.stock:
            quantity += 1
        else:
            ok, message = False, f'Only {product.stock} in stock.'
    elif action == 'dec':
        if quantity > 1:
            quantity -= 1
        else:
            ok, message = False, 'Minimum quantity is 1.'

    cart[code] = quantity
    _save_cart(request, cart)

    return JsonResponse({
        'ok': ok,
        'message': message,
        'quantity': quantity,
        'line_total': f'{product.price * quantity:.2f}',
        'subtotal': f'{_cart_subtotal(request):.2f}',
        'cart_count': sum(cart.values()),
    })


@require_POST
def remove_from_cart(request):
    code = request.POST.get('code')
    cart = _get_cart(request)
    name = 'Item'
    if code in cart:
        del cart[code]
        _save_cart(request, cart)
        product = Product.objects.filter(code=code).first()
        if product:
            name = f'{product.manufacturer} {product.model}'

    return JsonResponse({
        'ok': True,
        'message': f'{name} removed from your cart.',
        'subtotal': f'{_cart_subtotal(request):.2f}',
        'cart_count': sum(cart.values()),
        'empty': len(cart) == 0,
    })
