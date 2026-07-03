from django.shortcuts import render
from django.http import HttpResponse

def home(request):
    return render(request, 'home/welcome.html', {})

def products(request):
    return HttpResponse("Products page!")

def about(request):
    return HttpResponse("About page!")

def contact(request):
    return HttpResponse("Contact page!")
