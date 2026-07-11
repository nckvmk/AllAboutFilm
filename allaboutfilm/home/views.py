from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse

from .forms import ContactForm
from .models import Product, Camera, Lens, Film

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

def cart(request):
    return render(request, 'home/cart.html')
