from decimal import Decimal

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST

from .forms import ContactForm
from .models import Product, Camera, Lens, Film, ShippingMethod, GearCondition

def home(request):
    return render(request, 'home/welcome.html')

# Price buckets. Each entry: (key, dropdown label, ORM lookups). Upper bound is
# inclusive; the next bucket starts just above it, so they don't overlap.
GEAR_PRICE_RANGES = [
    ('under50', 'Under €50', {'price__lt': 50}),
    ('50-100', '€50 – €100', {'price__gte': 50, 'price__lte': 100}),
    ('100-500', '€100 – €500', {'price__gt': 100, 'price__lte': 500}),
    ('500-1000', '€500 – €1000', {'price__gt': 500, 'price__lte': 1000}),
    ('1000plus', '€1000 and above', {'price__gt': 1000}),
]

FILM_PRICE_RANGES = [
    ('under10', 'Under €10', {'price__lt': 10}),
    ('10-30', '€10 – €30', {'price__gte': 10, 'price__lte': 30}),
    ('30-50', '€30 – €50', {'price__gt': 30, 'price__lte': 50}),
    ('50plus', '€50 and above', {'price__gt': 50}),
]

FILM_ISO_CHOICES = [6, 25, 50, 100, 125, 160, 200, 320, 400, 800, 1600, 6400]

# Sort options. `None` means "leave the natural order". "Most Recent" uses the
# code PK descending: codes are zero-padded and per-category (C000, C001, …) so
# a higher code == newer item.
SORT_OPTIONS = [
    ('none', 'No sorting', None),
    ('recent', 'Most Recent', '-code'),
    ('price_asc', 'Price: Ascending', 'price'),
    ('price_desc', 'Price: Descending', '-price'),
]
DEFAULT_SORT = 'none'


def _render_catalog(request, queryset, page_title, empty_message, filter_specs, price_ranges):
    """Apply the dropdown filters from the query string to `queryset` and render
    the shared catalog template. `filter_specs` describes each exact-match
    dropdown; price is handled separately via `price_ranges`."""
    filters = []
    for spec in filter_specs:
        allowed = {str(value) for value, _ in spec['options']}
        selected = request.GET.get(spec['name'], '')
        if selected not in allowed:
            selected = ''  # ignore anything not offered by the dropdown
        if selected:
            queryset = queryset.filter(**{spec['field']: selected})
        filters.append({
            'name': spec['name'],
            'label': spec['label'],
            'all_label': spec['all_label'],
            'options': spec['options'],
            'selected': selected,
        })

    price_lookup = {key: lookups for key, _, lookups in price_ranges}
    price_selected = request.GET.get('price', '')
    if price_selected not in price_lookup:
        price_selected = ''
    if price_selected:
        queryset = queryset.filter(**price_lookup[price_selected])
    filters.append({
        'name': 'price',
        'label': 'Price',
        'all_label': 'Any price',
        'options': [(key, label) for key, label, _ in price_ranges],
        'selected': price_selected,
    })

    # Sorting (shared across all catalogs).
    sort_lookup = {key: order_by for key, _, order_by in SORT_OPTIONS}
    sort_selected = request.GET.get('sort', DEFAULT_SORT)
    if sort_selected not in sort_lookup:
        sort_selected = DEFAULT_SORT
    order_by = sort_lookup[sort_selected]
    if order_by:
        queryset = queryset.order_by(order_by)

    return render(request, 'home/catalog.html', {
        'items': queryset,
        'page_title': page_title,
        'empty_message': empty_message,
        'filters': filters,
        'has_filters_applied': any(f['selected'] for f in filters),
        'sort_options': [(key, label) for key, label, _ in SORT_OPTIONS],
        'sort_selected': sort_selected,
    })


def cameras(request):
    manufacturers = (Camera.objects.values_list('manufacturer', flat=True)
                     .distinct().order_by('manufacturer'))
    specs = [
        {'name': 'type', 'label': 'Type', 'all_label': 'All types',
         'field': 'type', 'options': Camera.Type.choices},
        {'name': 'manufacturer', 'label': 'Manufacturer', 'all_label': 'All manufacturers',
         'field': 'manufacturer', 'options': [(m, m) for m in manufacturers]},
        {'name': 'condition', 'label': 'Condition', 'all_label': 'All conditions',
         'field': 'condition', 'options': GearCondition.choices},
    ]
    return _render_catalog(
        request,
        Camera.objects.prefetch_related('images').all(),
        'Cameras', 'No cameras available at the moment.',
        specs, GEAR_PRICE_RANGES,
    )


def lenses(request):
    manufacturers = (Lens.objects.values_list('manufacturer', flat=True)
                     .distinct().order_by('manufacturer'))
    specs = [
        {'name': 'type', 'label': 'Type', 'all_label': 'All types',
         'field': 'type', 'options': Lens.Type.choices},
        {'name': 'manufacturer', 'label': 'Manufacturer', 'all_label': 'All manufacturers',
         'field': 'manufacturer', 'options': [(m, m) for m in manufacturers]},
        {'name': 'condition', 'label': 'Condition', 'all_label': 'All conditions',
         'field': 'condition', 'options': GearCondition.choices},
    ]
    return _render_catalog(
        request,
        Lens.objects.prefetch_related('images').all(),
        'Lenses', 'No lenses available at the moment.',
        specs, GEAR_PRICE_RANGES,
    )


def film(request):
    manufacturers = (Film.objects.values_list('manufacturer', flat=True)
                     .distinct().order_by('manufacturer'))
    specs = [
        {'name': 'film_type', 'label': 'Type', 'all_label': 'All types',
         'field': 'film_type', 'options': Film.FilmType.choices},
        {'name': 'format', 'label': 'Format', 'all_label': 'All formats',
         'field': 'format', 'options': Film.Format.choices},
        {'name': 'manufacturer', 'label': 'Manufacturer', 'all_label': 'All manufacturers',
         'field': 'manufacturer', 'options': [(m, m) for m in manufacturers]},
        {'name': 'iso', 'label': 'ISO', 'all_label': 'All ISO',
         'field': 'iso', 'options': [(str(i), str(i)) for i in FILM_ISO_CHOICES]},
        {'name': 'condition', 'label': 'Condition', 'all_label': 'All conditions',
         'field': 'condition', 'options': Film.Condition.choices},
    ]
    return _render_catalog(
        request,
        Film.objects.prefetch_related('images').all(),
        'Film', 'No film available at the moment.',
        specs, FILM_PRICE_RANGES,
    )

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
