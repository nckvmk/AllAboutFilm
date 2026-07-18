import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import ProtectedError, F, Count, Q, Avg
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from django.template.loader import render_to_string

from .forms import (
    ContactForm, LoginForm, RegistrationForm, PasswordRecoveryForm,
    CustomerProfileForm, CheckoutForm, CameraForm, LensForm, FilmForm,
    OrderEditForm,
)
from .models import (
    Product, Camera, Lens, Film, ShippingMethod, GearCondition,
    Order, OrderItem, WishlistItem, ProductImage, CustomerReport, Feedback,
)

# Visible-review aggregates (hidden reviews don't count toward the public score).
VISIBLE_FEEDBACK = Q(feedback__hidden=False)
RATING_ANNOTATIONS = {
    'avg_rating': Avg('feedback__rating', filter=VISIBLE_FEEDBACK),
    'review_count': Count('feedback', filter=VISIBLE_FEEDBACK),
}

INVENTORY_FORMS = {'cameras': CameraForm, 'lenses': LensForm, 'film': FilmForm}

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
        Film.objects.prefetch_related('images').annotate(**RATING_ANNOTATIONS),
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

    context = {
        'item': item,
        'images': item.images.all(),
        'back_url': back_url,
        'category_label': category_label,
    }
    # Reviews only apply to film. Show the visible ones plus the average.
    if product.category == Product.Category.FILM:
        reviews = (Feedback.objects.filter(product=product, hidden=False)
                   .select_related('user'))
        stats = reviews.aggregate(avg=Avg('rating'), count=Count('id'))
        context['reviews'] = reviews
        context['avg_rating'] = stats['avg']
        context['review_count'] = stats['count']
    return render(request, 'home/item_detail.html', context)

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
            elif not user_obj.check_password(password):
                form.add_error('username_or_email', 'The username/email provided is not valid.')
                form.add_error('password', 'The password provided is not valid.')
            elif user_obj.is_superuser:
                # The site admin manages everything through the Django admin
                # interface, not the storefront login.
                form.add_error('username_or_email', 'Administrator accounts must log in through the admin interface.')
            elif not user_obj.is_active:
                form.add_error('username_or_email',
                               'Your account has been suspended. Please contact us at info@aaf.com to resolve the issue.')
            else:
                user = authenticate(request, username=user_obj.username, password=password)
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
        'singular': 'Camera',
        'columns': ['Code', 'Manufacturer', 'Model', 'Type', 'Serial No.', 'Condition', 'Price', 'Stock'],
        'cells': lambda o: [o.code, o.manufacturer, o.model, o.get_type_display(),
                            o.serial_number, o.get_condition_display(), f'€{o.price}', o.stock],
    },
    'lenses': {
        'model': Lens,
        'label': 'Lenses',
        'singular': 'Lens',
        'columns': ['Code', 'Manufacturer', 'Model', 'Type', 'Serial No.', 'Condition', 'Price', 'Stock'],
        'cells': lambda o: [o.code, o.manufacturer, o.model, o.get_type_display(),
                            o.serial_number, o.get_condition_display(), f'€{o.price}', o.stock],
    },
    'film': {
        'model': Film,
        'label': 'Film',
        'singular': 'Film',
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


# User management: managers can moderate customers and employees.
USER_MGMT_CONFIG = {
    'employees': {'group': 'Employee', 'label': 'Employees'},
    'customers': {'group': 'Customer', 'label': 'Customers'},
}


def _users_context(category):
    config = USER_MGMT_CONFIG.get(category, USER_MGMT_CONFIG['employees'])
    User = get_user_model()
    users = (User.objects
             .filter(groups__name=config['group'])
             .annotate(pending_reports=Count(
                 'reports_received', filter=Q(reports_received__resolved=False)))
             .order_by('username'))
    return {
        'user_category': category,
        'user_category_label': config['label'],
        'users': users,
    }


def _orders_context():
    """All placed orders, newest first, for the manager order panel."""
    orders = (Order.objects
              .select_related('user')
              .prefetch_related('items'))
    return {'all_orders': orders}


def _customer_orders(user):
    """The customer's orders with per-order review state attached, so the My
    Orders panel can show 'Reviewed and Rated' vs 'Leave Feedback'. Reviews only
    apply to film lines."""
    orders = list(user.orders.prefetch_related('items__product', 'feedback'))
    for order in orders:
        film_items = [oi for oi in order.items.all()
                      if oi.product.category == Product.Category.FILM]
        reviewed = {f.product_id for f in order.feedback.all()}
        order.has_film = bool(film_items)
        order.all_reviewed = order.has_film and all(
            oi.product.code in reviewed for oi in film_items
        )
    return orders


def _feedback_context():
    """Every review for the staff moderation panel — flagged ones first so the
    manager sees what needs attention, then newest."""
    feedback = (Feedback.objects
                .select_related('user', 'product', 'flagged_by')
                .order_by('-flagged', '-created_at'))
    return {
        'all_feedback': feedback,
        'flagged_feedback_count': sum(1 for f in feedback if f.flagged),
    }


def _account_dashboard(request):
    """The logged-in account page. Everyone gets the Account Administration
    panel; customers also see wishlist/orders. Managers and employees share the
    inventory / users / orders panels but with different permissions."""
    user = request.user
    groups = set(user.groups.values_list('name', flat=True))
    is_customer = 'Customer' in groups
    is_manager = 'Manager' in groups
    is_employee = 'Employee' in groups and not is_manager
    is_staff_member = is_manager or is_employee
    has_panel = is_customer or is_staff_member

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
        'is_employee': is_employee,
        'is_staff_member': is_staff_member,
        'has_panel': has_panel,
        'profile_form': profile_form,
    }
    if is_customer:
        context['wishlist_items'] = WishlistItem.objects.filter(user=user).select_related('product').prefetch_related('product__images')
        context['orders'] = _customer_orders(user)
    if is_staff_member:
        context.update(_inventory_context('cameras'))
        # Managers moderate employees by default; employees only see customers.
        context.update(_users_context('employees' if is_manager else 'customers'))
        context.update(_orders_context())
        context.update(_feedback_context())
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
# Manager / employee: shared staff panels
# ---------------------------------------------------------------------------
def _is_manager(user):
    return user.groups.filter(name='Manager').exists()


def _is_employee(user):
    return user.groups.filter(name='Employee').exists()


def _is_staff_member(user):
    """A manager or an employee — the two roles that share the staff panels."""
    return user.groups.filter(name__in=['Manager', 'Employee']).exists()


def _role_flags(user):
    """Role flags for partials rendered over AJAX (managers and employees see the
    same tables but with different actions)."""
    is_manager = _is_manager(user)
    return {'is_manager': is_manager, 'is_employee': _is_employee(user) and not is_manager}


@login_required
def manager_inventory(request):
    """Returns the inventory table partial for the chosen category (AJAX)."""
    if not _is_staff_member(request.user):
        return HttpResponse(status=403)
    category = request.GET.get('category', 'cameras')
    if category not in INVENTORY_CONFIG:
        category = 'cameras'
    return render(request, 'home/_inventory_table.html',
                  {**_inventory_context(category), **_role_flags(request.user)})


def _stock_form_context(product, error=None):
    is_unique = product.category in (Product.Category.CAMERA, Product.Category.LENS)
    return {
        'product': product,
        'is_unique': is_unique,
        'max_stock': 1 if is_unique else None,
        'error': error,
    }


@login_required
def stock_form(request):
    """Minimal stock-only edit modal (employees may only change stock)."""
    if not _is_staff_member(request.user):
        return HttpResponse(status=403)
    product = get_object_or_404(Product, code=request.GET.get('code'))
    return render(request, 'home/_stock_form.html', _stock_form_context(product))


@require_POST
@login_required
def update_stock(request):
    if not _is_staff_member(request.user):
        return JsonResponse({'ok': False, 'message': 'Staff only.'}, status=403)
    product = get_object_or_404(Product, code=request.POST.get('code'))
    is_unique = product.category in (Product.Category.CAMERA, Product.Category.LENS)

    error = None
    try:
        stock = int((request.POST.get('stock') or '').strip())
    except ValueError:
        error = 'Enter a whole number.'
    else:
        if stock < 0:
            error = 'Stock cannot be negative.'
        elif is_unique and stock > 1:
            error = 'Cameras and lenses are unique items: stock can only be 0 or 1.'

    if error:
        html = render_to_string('home/_stock_form.html',
                                _stock_form_context(product, error), request=request)
        return JsonResponse({'ok': False, 'html': html})

    product.stock = stock
    product.save(update_fields=['stock'])
    return JsonResponse({
        'ok': True,
        'message': f'{product.manufacturer} {product.model} stock set to {stock}.',
    })


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


def _image_slots(instance, category, image_errors=None):
    """Build the photo-slot list for the add/edit form (4 slots, 1 for film)."""
    image_count = 1 if category == 'film' else 4
    existing = list(instance.images.all()) if instance else []
    return [{
        'index': i + 1,
        'existing': existing[i] if i < len(existing) else None,
        'error': (image_errors or {}).get(i + 1),
    } for i in range(image_count)]


def _inventory_form_context(category, mode, code, form, instance, image_errors=None, request=None):
    return {
        'form': form,
        'category': category,
        'category_singular': INVENTORY_CONFIG[category]['singular'],
        'mode': mode,
        'code': code,
        'slots': _image_slots(instance, category, image_errors),
    }


@login_required
def inventory_form(request):
    """Return the add/edit modal form for a category (AJAX)."""
    if not _is_manager(request.user):
        return HttpResponse(status=403)
    category = request.GET.get('category', 'cameras')
    if category not in INVENTORY_CONFIG:
        category = 'cameras'
    code = request.GET.get('code')
    FormClass = INVENTORY_FORMS[category]
    model = INVENTORY_CONFIG[category]['model']

    if code:
        instance = get_object_or_404(model, code=code)
        form, mode = FormClass(instance=instance), 'edit'
    else:
        instance, form, mode = None, FormClass(), 'add'

    return render(request, 'home/_inventory_form.html',
                  _inventory_form_context(category, mode, code, form, instance))


@require_POST
@login_required
def inventory_save(request):
    if not _is_manager(request.user):
        return JsonResponse({'ok': False, 'message': 'Managers only.'}, status=403)
    category = request.POST.get('category')
    if category not in INVENTORY_CONFIG:
        return JsonResponse({'ok': False, 'message': 'Invalid category.'}, status=400)

    code = request.POST.get('code')
    FormClass = INVENTORY_FORMS[category]
    model = INVENTORY_CONFIG[category]['model']
    image_count = 1 if category == 'film' else 4

    if code:
        instance = get_object_or_404(model, code=code)
        form, mode = FormClass(request.POST, instance=instance), 'edit'
    else:
        instance, form, mode = None, FormClass(request.POST), 'add'

    existing = list(instance.images.all()) if instance else []

    # Validate the photo slots.
    image_errors = {}
    for i in range(image_count):
        idx = i + 1
        file = request.FILES.get(f'image_{idx}')
        alt = (request.POST.get(f'alt_{idx}') or '').strip()
        has_existing = i < len(existing)
        problems = []
        if not file and not has_existing:
            problems.append('a photo')
        elif file and file.content_type not in ('image/jpeg', 'image/png'):
            problems.append('a JPG or PNG photo')
        if not alt:
            problems.append('alt text')
        if problems:
            image_errors[idx] = 'Please provide ' + ' and '.join(problems) + '.'

    if form.is_valid() and not image_errors:
        with transaction.atomic():
            obj = form.save()
            product = obj.product_ptr
            current = list(obj.images.all())
            for i in range(image_count):
                idx = i + 1
                file = request.FILES.get(f'image_{idx}')
                alt = (request.POST.get(f'alt_{idx}') or '').strip()
                if i < len(current):
                    img = current[i]
                    if file:
                        img.image = file
                    img.alt_text, img.position = alt, i
                    img.save()
                else:
                    ProductImage.objects.create(product=product, image=file, alt_text=alt, position=i)
        verb = 'added' if mode == 'add' else 'updated'
        return JsonResponse({'ok': True, 'message': f'{obj.manufacturer} {obj.model} was {verb} successfully.'})

    # Invalid -> mark fields red and re-render the form with errors.
    for name in form.errors:
        if name in form.fields:
            widget = form.fields[name].widget
            widget.attrs['class'] = (widget.attrs.get('class', '') + ' is-invalid').strip()
    html = render_to_string(
        'home/_inventory_form.html',
        _inventory_form_context(category, mode, code, form, instance, image_errors),
        request=request,
    )
    return JsonResponse({'ok': False, 'html': html})


# ---------------------------------------------------------------------------
# User management. Managers suspend/unsuspend customers & employees; employees
# only view customers and report them to the manager.
# ---------------------------------------------------------------------------
@login_required
def manager_users(request):
    """Return the users table partial for a category (AJAX)."""
    if not _is_staff_member(request.user):
        return HttpResponse(status=403)
    category = request.GET.get('category', 'employees')
    # Employees may only ever see customers.
    if _is_employee(request.user) and not _is_manager(request.user):
        category = 'customers'
    if category not in USER_MGMT_CONFIG:
        category = 'customers'
    return render(request, 'home/_users_table.html',
                  {**_users_context(category), **_role_flags(request.user)})


@require_POST
@login_required
def report_customer(request):
    """An employee (or manager) flags a customer for the manager's attention."""
    if not _is_staff_member(request.user):
        return JsonResponse({'ok': False, 'message': 'Staff only.'}, status=403)
    User = get_user_model()
    target = User.objects.filter(pk=request.POST.get('user_id')).first()
    if target is None:
        return JsonResponse({'ok': False, 'message': 'User not found.'}, status=404)
    groups = set(target.groups.values_list('name', flat=True))
    if 'Customer' not in groups or target.is_superuser:
        return JsonResponse({'ok': False, 'message': 'Only customers can be reported.'}, status=400)

    reason = (request.POST.get('reason') or '').strip()[:300]
    CustomerReport.objects.create(customer=target, reported_by=request.user, reason=reason)
    pending = CustomerReport.objects.filter(customer=target, resolved=False).count()
    return JsonResponse({
        'ok': True,
        'pending': pending,
        'message': f'{target.username} was reported to the manager.',
    })


@login_required
def view_reports(request):
    """Manager: the pending reports for a customer, rendered for the popup."""
    if not _is_manager(request.user):
        return HttpResponse(status=403)
    User = get_user_model()
    target = get_object_or_404(User, pk=request.GET.get('user_id'))
    reports = (CustomerReport.objects
               .filter(customer=target, resolved=False)
               .select_related('reported_by'))
    return render(request, 'home/_reports_list.html', {'target': target, 'reports': reports})


@require_POST
@login_required
def resolve_reports(request):
    """Manager dismisses all pending reports for a customer."""
    if not _is_manager(request.user):
        return JsonResponse({'ok': False, 'message': 'Managers only.'}, status=403)
    User = get_user_model()
    target = User.objects.filter(pk=request.POST.get('user_id')).first()
    if target is None:
        return JsonResponse({'ok': False, 'message': 'User not found.'}, status=404)
    count = CustomerReport.objects.filter(customer=target, resolved=False).update(resolved=True)
    return JsonResponse({
        'ok': True,
        'message': f'Dismissed {count} report{"" if count == 1 else "s"} for {target.username}.',
    })


@require_POST
@login_required
def toggle_user_status(request):
    if not _is_manager(request.user):
        return JsonResponse({'ok': False, 'message': 'Managers only.'}, status=403)
    User = get_user_model()
    target = User.objects.filter(pk=request.POST.get('user_id')).first()
    if target is None:
        return JsonResponse({'ok': False, 'message': 'User not found.'}, status=404)

    # Managers may only moderate customers/employees — not admins, other
    # managers, or themselves.
    groups = set(target.groups.values_list('name', flat=True))
    if target == request.user or target.is_superuser or 'Manager' in groups:
        return JsonResponse({'ok': False, 'message': 'You cannot change this account.'}, status=403)
    if not (groups & {'Customer', 'Employee'}):
        return JsonResponse({'ok': False, 'message': 'This account cannot be moderated.'}, status=400)

    target.is_active = not target.is_active
    target.save(update_fields=['is_active'])
    status = 'reactivated' if target.is_active else 'suspended'
    return JsonResponse({
        'ok': True,
        'is_active': target.is_active,
        'message': f'{target.username} was {status}.',
    })


# ---------------------------------------------------------------------------
# Manager: order management (edit items / shipping / status, or delete)
# ---------------------------------------------------------------------------
def _order_edit_context(order, form, error_list=None):
    return {
        'order': order,
        'form': form,
        'items': order.items.select_related('product'),
        'products': Product.objects.order_by('code'),
        'error_list': error_list or [],
    }


@login_required
def manager_orders(request):
    """Return the orders table partial (AJAX, used to refresh after edit/delete)."""
    if not _is_staff_member(request.user):
        return HttpResponse(status=403)
    return render(request, 'home/_orders_table.html', _orders_context())


@login_required
def order_edit_form(request):
    """Return the edit modal for a single order (AJAX)."""
    if not _is_staff_member(request.user):
        return HttpResponse(status=403)
    order = get_object_or_404(Order, pk=request.GET.get('order_id'))
    form = OrderEditForm(instance=order)
    return render(request, 'home/_order_edit_form.html', _order_edit_context(order, form))


@require_POST
@login_required
def order_save(request):
    if not _is_staff_member(request.user):
        return JsonResponse({'ok': False, 'message': 'Staff only.'}, status=403)
    order = get_object_or_404(Order, pk=request.POST.get('order_id'))
    form = OrderEditForm(request.POST, instance=order)

    errors = []

    # --- Existing items: a new quantity, or removal ---
    item_actions = []  # (OrderItem, 'remove') or (OrderItem, new_quantity)
    for item in order.items.select_related('product'):
        label = f'{item.product.manufacturer} {item.product.model}'
        if request.POST.get(f'remove_{item.id}'):
            item_actions.append((item, 'remove'))
            continue
        raw = (request.POST.get(f'qty_{item.id}') or '').strip()
        try:
            new_qty = int(raw)
        except ValueError:
            errors.append(f'{label}: enter a valid quantity.')
            continue
        max_qty = item.quantity + item.product.stock
        if new_qty < 1:
            errors.append(f'{label}: quantity must be at least 1 (or tick Remove).')
        elif new_qty > max_qty:
            errors.append(f'{label}: only {max_qty} in stock.')
        else:
            item_actions.append((item, new_qty))

    # --- New items to add ---
    existing_codes = {i.product.code for i in order.items.all()}
    new_adds = []  # (Product, quantity)
    seen = set()
    for code, raw in zip(request.POST.getlist('new_product'),
                         request.POST.getlist('new_qty')):
        code = (code or '').strip()
        if not code:
            continue
        product = Product.objects.filter(code=code).first()
        if product is None:
            errors.append(f'{code}: product not found.')
            continue
        label = f'{product.manufacturer} {product.model}'
        if code in existing_codes or code in seen:
            errors.append(f'{label}: already in the order — edit its quantity above instead.')
            continue
        seen.add(code)
        try:
            qty = int((raw or '').strip())
        except ValueError:
            errors.append(f'{label}: enter a valid quantity.')
            continue
        if qty < 1:
            errors.append(f'{label}: quantity must be at least 1.')
        elif qty > product.stock:
            errors.append(f'{label}: only {product.stock} in stock.')
        else:
            new_adds.append((product, qty))

    # --- An order can't be emptied (only flag this once other item issues,
    # which may be the real cause, are resolved) ---
    kept = [a for a in item_actions if a[1] != 'remove']
    if not kept and not new_adds and not errors:
        errors.append('An order must keep at least one item.')

    if form.is_valid() and not errors:
        with transaction.atomic():
            for item, action in item_actions:
                if action == 'remove':
                    Product.objects.filter(pk=item.product_id).update(stock=F('stock') + item.quantity)
                    item.delete()
                else:
                    delta = action - item.quantity
                    if delta:
                        Product.objects.filter(pk=item.product_id).update(stock=F('stock') - delta)
                        item.quantity = action
                        item.save(update_fields=['quantity'])
            for product, qty in new_adds:
                Product.objects.filter(pk=product.pk).update(stock=F('stock') - qty)
                OrderItem.objects.create(order=order, product=product,
                                         quantity=qty, price_at_purchase=product.price)
            order = form.save(commit=False)
            subtotal = sum((i.quantity * i.price_at_purchase for i in order.items.all()), Decimal('0'))
            order.subtotal = subtotal
            order.total = subtotal + order.shipping_cost
            order.save()
        return JsonResponse({'ok': True, 'message': f'Order #{order.pk} was updated.'})

    # Invalid -> mark form fields red and re-render with the error list.
    for name in form.errors:
        if name in form.fields:
            widget = form.fields[name].widget
            widget.attrs['class'] = (widget.attrs.get('class', '') + ' is-invalid').strip()
    html = render_to_string(
        'home/_order_edit_form.html',
        _order_edit_context(order, form, errors),
        request=request,
    )
    return JsonResponse({'ok': False, 'html': html})


@require_POST
@login_required
def order_delete(request):
    if not _is_staff_member(request.user):
        return JsonResponse({'ok': False, 'message': 'Staff only.'}, status=403)
    order = get_object_or_404(Order, pk=request.POST.get('order_id'))
    num = order.pk
    with transaction.atomic():
        # Voiding the order returns its items to stock.
        for item in order.items.select_related('product'):
            Product.objects.filter(pk=item.product_id).update(stock=F('stock') + item.quantity)
        order.delete()
    return JsonResponse({'ok': True, 'message': f'Order #{num} was deleted.'})


# ---------------------------------------------------------------------------
# Customer reviews (feedback on purchased film)
# ---------------------------------------------------------------------------
def _order_film_items(order):
    """The film order-lines of an order, each paired with the customer's existing
    review for it (or None). Only film is reviewable."""
    reviews = {f.product_id: f for f in order.feedback.all()}
    items = []
    for oi in order.items.select_related('product'):
        if oi.product.category == Product.Category.FILM:
            items.append({'product': oi.product, 'review': reviews.get(oi.product.code)})
    return items


@login_required
def review_form(request):
    """Return the 'Leave Feedback' modal for one of the customer's own orders —
    either the rating form (order Completed) or a 'not yet' notice."""
    order = get_object_or_404(Order, pk=request.GET.get('order_id'), user=request.user)
    film_items = _order_film_items(order)
    return render(request, 'home/_review_form.html', {
        'order': order,
        'film_items': film_items,
        'has_film': bool(film_items),
        'completed': order.status == Order.Status.COMPLETED,
    })


@require_POST
@login_required
def review_submit(request):
    order = get_object_or_404(Order, pk=request.POST.get('order_id'), user=request.user)
    # Validation problems return HTTP 200 with ok=False (matching the rest of the
    # app's AJAX endpoints) so the client's .done() handler can surface the
    # message / field errors; jQuery routes non-2xx to .fail() instead.
    if order.status != Order.Status.COMPLETED:
        return JsonResponse(
            {'ok': False, 'message': 'You can leave feedback once this order is Completed.'})

    film_items = _order_film_items(order)
    if not film_items:
        return JsonResponse({'ok': False, 'message': 'This order has no film to review.'})

    to_save = []   # (product, rating, text)
    errors = {}    # {product_code: message}
    any_input = False
    for entry in film_items:
        product = entry['product']
        if entry['review'] is not None:
            continue  # already reviewed — don't touch it
        raw_rating = (request.POST.get(f'rating_{product.code}') or '').strip()
        text = (request.POST.get(f'text_{product.code}') or '').strip()
        if not raw_rating and not text:
            continue  # left blank — skip
        any_input = True
        try:
            rating = int(raw_rating)
        except ValueError:
            errors[product.code] = 'Please choose a star rating.'
            continue
        if not 1 <= rating <= 5:
            errors[product.code] = 'Rating must be between 1 and 5 stars.'
        elif len(text) > 500:
            errors[product.code] = 'Reviews are limited to 500 characters.'
        else:
            to_save.append((product, rating, text))

    if not any_input:
        return JsonResponse({'ok': False, 'message': 'Please rate at least one item.'})
    if errors:
        return JsonResponse({'ok': False, 'errors': errors})

    for product, rating, text in to_save:
        Feedback.objects.update_or_create(
            order=order, product=product,
            defaults={'user': request.user, 'rating': rating, 'text': text},
        )

    reviewed = set(Feedback.objects.filter(order=order).values_list('product_id', flat=True))
    all_reviewed = all(e['product'].code in reviewed for e in film_items)
    return JsonResponse({
        'ok': True,
        'all_reviewed': all_reviewed,
        'message': 'Thanks! Your feedback has been recorded.',
    })


# ---------------------------------------------------------------------------
# Staff: review moderation (flag / hide / delete)
# ---------------------------------------------------------------------------
@login_required
def manager_feedback(request):
    """Return the feedback moderation table partial (AJAX refresh)."""
    if not _is_staff_member(request.user):
        return HttpResponse(status=403)
    return render(request, 'home/_feedback_table.html',
                  {**_feedback_context(), **_role_flags(request.user)})


@require_POST
@login_required
def feedback_flag(request):
    """Employee flags a review for the manager's attention."""
    if not _is_staff_member(request.user):
        return JsonResponse({'ok': False, 'message': 'Staff only.'}, status=403)
    review = get_object_or_404(Feedback, pk=request.POST.get('feedback_id'))
    review.flagged = True
    review.flagged_by = request.user
    review.save(update_fields=['flagged', 'flagged_by'])
    return JsonResponse({'ok': True, 'message': 'Review flagged for the manager.'})


@require_POST
@login_required
def feedback_hide(request):
    """Employee or manager hides / unhides a review. A manager acting on it also
    clears any pending flag (they've reviewed it); an employee hiding it leaves
    the flag standing so the manager still gets notified."""
    if not _is_staff_member(request.user):
        return JsonResponse({'ok': False, 'message': 'Staff only.'}, status=403)
    review = get_object_or_404(Feedback, pk=request.POST.get('feedback_id'))
    review.hidden = not review.hidden
    fields = ['hidden']
    if _is_manager(request.user):
        review.flagged = False
        review.flagged_by = None
        fields += ['flagged', 'flagged_by']
    review.save(update_fields=fields)
    return JsonResponse({
        'ok': True,
        'hidden': review.hidden,
        'message': 'Review hidden.' if review.hidden else 'Review is visible again.',
    })


@require_POST
@login_required
def feedback_delete(request):
    """Manager deletes a review outright."""
    if not _is_manager(request.user):
        return JsonResponse({'ok': False, 'message': 'Managers only.'}, status=403)
    review = Feedback.objects.filter(pk=request.POST.get('feedback_id')).first()
    if review is None:
        return JsonResponse({'ok': False, 'message': 'Review not found.'}, status=404)
    review.delete()
    return JsonResponse({'ok': True, 'message': 'Review deleted.'})
