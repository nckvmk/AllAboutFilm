from django.shortcuts import render
from django.http import HttpResponse

def home(request):
    return render(request, 'home/welcome.html')

def catalog(request):
    return render(request, 'home/catalog.html')

def about(request):
    return render(request, 'home/about.html')

def contact(request):
    return render(request, 'home/contact.html')
