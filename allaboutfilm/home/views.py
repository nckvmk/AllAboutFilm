from django.shortcuts import render
from django.http import HttpResponse

from .forms import ContactForm

def home(request):
    return render(request, 'home/welcome.html')

def catalog(request):
    return render(request, 'home/catalog.html')

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
