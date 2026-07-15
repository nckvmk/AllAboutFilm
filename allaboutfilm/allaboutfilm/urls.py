"""
URL configuration for allaboutfilm project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from home import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='welcome'),
    path('cameras/', views.cameras, name='cameras'),
    path('lenses/', views.lenses, name='lenses'),
    path('film/', views.film, name='film'),
    path('item/<str:code>/', views.item_detail, name='item_detail'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('shipping/', views.shipping, name='shipping'),
    path('payment/', views.payment, name='payment'),
    path('account/', views.account, name='account'),
    path('register/', views.register, name='register'),
    path('recover/', views.password_recovery, name='recover'),
    path('logout/', views.logout_view, name='logout'),
    path('cart/', views.cart, name='cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/', views.update_cart, name='update_cart'),
    path('cart/remove/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('order/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('wishlist/toggle/', views.toggle_wishlist, name='toggle_wishlist'),
    path('wishlist/remove/', views.remove_from_wishlist, name='remove_from_wishlist'),
]

# Serve user-uploaded media files during development.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
