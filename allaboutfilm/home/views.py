import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import ProtectedError
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import (
    ContactForm, LoginForm, RegistrationForm, PasswordRecoveryForm,
    CustomerProfileForm, CheckoutForm,
)
from .models import (
    Product, Camera, Lens, Film, ShippingMethod, GearCondition,
    Order, OrderItem, WishlistItem,
)

def home(request):
    # "Just In" showcases the most recent camera and lens (highest code = newest).
    latest_camera = Camera.objects.prefetch_related('images').order_by('-code').first()
    latest_lens = Lens.objects.prefetch_related('images').order_by('-code').first()
    just_in = [item for item in (latest_camera, latest_lens) if item is not None]
    return render(request, 'home/welcome.html', {'just_in': just_in})

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

def shipping(request):
    return render(request, 'home/shipping.html')

def payment(request):
    return render(request, 'home/payment.html')

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
    # Logged in -> show the account dashboard.
    if request.user.is_authenticated:
        return _account_dashboard(request)

    # Otherwise the account page IS the login page.
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['username_or_email']
            password = form.cleaned_data['password']
            User = get_user_model()
            user_obj = (User.objects.filter(username__iexact=identifier).first()
                        or User.objects.filter(email__iexact=identifier).first())
            if user_obj is None:
                form.add_error('username_or_email', 'The username/email provided does not exist in our records.')
                form.add_error('password', 'The password provided does not exist in our records.')
            else:
                user = authenticate(request, username=user_obj.username, password=password)
                if user is None:
                    form.add_error('username_or_email', 'The username/email provided is not valid.')
                    form.add_error('password', 'The password provided is not valid.')
                elif user.is_superuser:
                    # The site admin manages everything through the Django admin
                    # interface, not the storefront login.
                    form.add_error('username_or_email', 'Administrator accounts must log in through the admin interface.')
                else:
                    login(request, user)
                    # "Remember me" unchecked -> session ends when the browser closes.
                    if not form.cleaned_data.get('remember_me'):
                        request.session.set_expiry(0)
                    next_url = form.cleaned_data.get('next')
                    if next_url and url_has_allowed_host_and_scheme(
                            next_url, allowed_hosts={request.get_host()}):
                        return redirect(next_url)
                    return redirect('account')
    else:
        form = LoginForm(initial={'next': request.GET.get('next', '')})
    return render(request, 'home/account.html', {'form': form})


# Inventory management table config, keyed by the dropdown value. `cells`
# returns the row values in the same order as `columns`.
INVENTORY_CONFIG = {
    'cameras': {
        'model': Camera,
        'label': 'Cameras',
        'columns': ['Code', 'Manufacturer', 'Model', 'Type', 'Serial No.', 'Condition', 'Price', 'Stock'],
        'cells': lambda o: [o.code, o.manufacturer, o.model, o.get_type_display(),
                            o.serial_number, o.get_condition_display(), f'€{o.price}', o.stock],
    },
    'lenses': {
        'model': Lens,
        'label': 'Lenses',
        'columns': ['Code', 'Manufacturer', 'Model', 'Type', 'Serial No.', 'Condition', 'Price', 'Stock'],
        'cells': lambda o: [o.code, o.manufacturer, o.model, o.get_type_display(),
                            o.serial_number, o.get_condition_display(), f'€{o.price}', o.stock],
    },
    'film': {
        'model': Film,
        'label': 'Film',
        'columns': ['Code', 'Manufacturer', 'Model', 'Format', 'Type', 'ISO', 'Condition', 'Price', 'Stock'],
        'cells': lambda o: [o.code, o.manufacturer, o.model, o.get_format_display(),
                            o.get_film_type_display(), o.iso, o.get_condition_display(), f'€{o.price}', o.stock],
    },
}


def _inventory_context(category):
    config = INVENTORY_CONFIG.get(category, INVENTORY_CONFIG['cameras'])
    items = config['model'].objects.order_by('code')
    return {
        'category': category,
        'columns': config['columns'],
        'rows': [{'code': o.code, 'cells': config['cells'](o)} for o in items],
    }


def _account_dashboard(request):
    """The logged-in account page. Everyone gets the Account Administration
    panel; customers also see wishlist/orders, managers see inventory."""
    user = request.user
    groups = set(user.groups.values_list('name', flat=True))
    is_customer = 'Customer' in groups
    is_manager = 'Manager' in groups
    has_panel = is_customer or is_manager

    profile_form = None
    if has_panel:
        if request.method == 'POST':
            profile_form = CustomerProfileForm(request.POST, request.FILES, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Your profile has been updated.')
                return redirect('account')
        else:
            profile_form = CustomerProfileForm(instance=user)

    context = {
        'is_customer': is_customer,
        'is_manager': is_manager,
        'has_panel': has_panel,
        'profile_form': profile_form,
    }
    if is_customer:
        context['wishlist_items'] = WishlistItem.objects.filter(user=user).select_related('product').prefetch_related('product__images')
        context['orders'] = user.orders.all()
    if is_manager:
        context.update(_inventory_context('cameras'))
    return render(request, 'home/account.html', context)


def register(request):
    if request.user.is_authenticated:
        return redirect('account')
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            User = get_user_model()
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
            )
            # New registrants are customers.
            customer_group = Group.objects.filter(name='Customer').first()
            if customer_group:
                user.groups.add(customer_group)
            messages.success(request, 'Registration successful! You can now log in.')
            return redirect('account')
    else:
        form = RegistrationForm()
    return render(request, 'home/register.html', {'form': form})


def password_recovery(request):
    if request.method == 'POST':
        form = PasswordRecoveryForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            user.set_password(form.cleaned_data['new_password'])
            user.save()
            messages.success(request, 'Your password has been reset. You can now log in.')
            return redirect('account')
    else:
        form = PasswordRecoveryForm()
    return render(request, 'home/recover.html', {'form': form})


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('welcome')


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


# ---------------------------------------------------------------------------
# Checkout & orders
# ---------------------------------------------------------------------------
def _cart_items(request):
    """Resolve the session cart into a list of {product, quantity, line_total}
    plus the subtotal."""
    cart = _get_cart(request)
    products = Product.objects.filter(code__in=cart.keys()).prefetch_related('images')
    items = []
    subtotal = Decimal('0.00')
    for product in products:
        quantity = cart.get(product.code, 0)
        line_total = product.price * quantity
        subtotal += line_total
        items.append({'product': product, 'quantity': quantity, 'line_total': line_total})
    return items, subtotal


@login_required
def checkout(request):
    items, subtotal = _cart_items(request)
    if not items:
        return redirect('cart')

    shipping_prices = {
        str(m.pk): float(m.price)
        for m in ShippingMethod.objects.filter(is_active=True)
    }

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Guard against stock changing since items were added to the cart.
            out_of_stock = [
                it for it in items if it['quantity'] > it['product'].stock
            ]
            if out_of_stock:
                for it in out_of_stock:
                    p = it['product']
                    messages.error(request, f'Only {p.stock} of {p.manufacturer} {p.model} left in stock.')
                return redirect('cart')

            order = _place_order(request, form, items, subtotal)
            _save_cart(request, {})  # empty the cart
            messages.success(request, 'Your order has been placed successfully!')
            return redirect('order_confirmation', order_id=order.pk)
        else:
            # Mark invalid fields so they render with the red Bootstrap border.
            for name in form.errors:
                if name in form.fields:
                    widget = form.fields[name].widget
                    widget.attrs['class'] = (widget.attrs.get('class', '') + ' is-invalid').strip()
    else:
        form = CheckoutForm(initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        })

    return render(request, 'home/checkout.html', {
        'form': form,
        'items': items,
        'subtotal': subtotal,
        'shipping_prices_json': json.dumps(shipping_prices),
    })


@transaction.atomic
def _place_order(request, form, items, subtotal):
    cd = form.cleaned_data
    same = cd['shipping_same_as_billing']
    shipping_method = cd['shipping_method']
    shipping_cost = shipping_method.price
    total = subtotal + shipping_cost

    order = Order.objects.create(
        user=request.user,
        first_name=cd['first_name'], last_name=cd['last_name'],
        email=cd['email'], phone=cd['phone'],
        billing_address=cd['billing_address'], billing_region=cd['billing_region'],
        billing_country=cd['billing_country'], billing_postal_code=cd['billing_postal_code'],
        shipping_same_as_billing=same,
        shipping_address=cd['billing_address'] if same else cd['shipping_address'],
        shipping_region=cd['billing_region'] if same else cd['shipping_region'],
        shipping_country=cd['billing_country'] if same else cd['shipping_country'],
        shipping_postal_code=cd['billing_postal_code'] if same else cd['shipping_postal_code'],
        payment_method=cd['payment_method'],
        shipping_method=shipping_method,
        shipping_cost=shipping_cost,
        subtotal=subtotal,
        total=total,
    )
    for it in items:
        product = it['product']
        OrderItem.objects.create(
            order=order, product=product,
            quantity=it['quantity'], price_at_purchase=product.price,
        )
        product.stock = max(0, product.stock - it['quantity'])
        product.save(update_fields=['stock'])
    return order


@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product'), pk=order_id, user=request.user
    )
    return render(request, 'home/order_confirmation.html', {'order': order})


# ---------------------------------------------------------------------------
# Wishlist
# ---------------------------------------------------------------------------
@require_POST
def toggle_wishlist(request):
    if not request.user.is_authenticated:
        return JsonResponse({
            'ok': False, 'login_required': True,
            'message': 'Please log in to use your wishlist.',
        })
    product = get_object_or_404(Product, code=request.POST.get('code'))
    item = WishlistItem.objects.filter(user=request.user, product=product).first()
    if item:
        item.delete()
        return JsonResponse({'ok': True, 'in_wishlist': False,
                             'message': f'{product.manufacturer} {product.model} removed from your wishlist.'})
    WishlistItem.objects.create(user=request.user, product=product)
    return JsonResponse({'ok': True, 'in_wishlist': True,
                         'message': f'{product.manufacturer} {product.model} added to your wishlist!'})


@require_POST
@login_required
def remove_from_wishlist(request):
    product = get_object_or_404(Product, code=request.POST.get('code'))
    WishlistItem.objects.filter(user=request.user, product=product).delete()
    empty = not WishlistItem.objects.filter(user=request.user).exists()
    return JsonResponse({'ok': True, 'empty': empty,
                         'message': f'{product.manufacturer} {product.model} removed from your wishlist.'})


# ---------------------------------------------------------------------------
# Manager: inventory management
# ---------------------------------------------------------------------------
def _is_manager(user):
    return user.groups.filter(name='Manager').exists()


@login_required
def manager_inventory(request):
    """Returns the inventory table partial for the chosen category (AJAX)."""
    if not _is_manager(request.user):
        return HttpResponse(status=403)
    category = request.GET.get('category', 'cameras')
    if category not in INVENTORY_CONFIG:
        category = 'cameras'
    return render(request, 'home/_inventory_table.html', _inventory_context(category))


@require_POST
@login_required
def delete_inventory_item(request):
    if not _is_manager(request.user):
        return JsonResponse({'ok': False, 'message': 'Managers only.'}, status=403)
    product = Product.objects.filter(code=request.POST.get('code')).first()
    if not product:
        return JsonResponse({'ok': False, 'message': 'Item not found.'}, status=404)
    name = f'{product.manufacturer} {product.model}'
    try:
        product.delete()
    except ProtectedError:
        return JsonResponse({'ok': False,
                             'message': f'{name} is part of an order and cannot be deleted.'})
    return JsonResponse({'ok': True, 'message': f'{name} was deleted.'})
