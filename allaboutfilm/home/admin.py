from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    User, Product, Camera, Lens, Film, ProductImage,
    Cart, CartItem, Order, OrderItem, ShippingMethod, WishlistItem,
)


admin.site.register(WishlistItem)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = ('code', 'manufacturer', 'model', 'type', 'condition', 'price', 'stock')
    list_filter = ('type', 'condition')
    search_fields = ('manufacturer', 'model', 'serial_number')
    exclude = ('category',)  # set automatically on save()
    inlines = [ProductImageInline]


@admin.register(Lens)
class LensAdmin(admin.ModelAdmin):
    list_display = ('code', 'manufacturer', 'model', 'type', 'condition', 'price', 'stock')
    list_filter = ('type', 'condition')
    search_fields = ('manufacturer', 'model', 'serial_number')
    exclude = ('category',)  # set automatically on save()
    inlines = [ProductImageInline]


@admin.register(Film)
class FilmAdmin(admin.ModelAdmin):
    list_display = ('code', 'manufacturer', 'model', 'format', 'film_type', 'iso', 'condition', 'price', 'stock')
    list_filter = ('format', 'film_type', 'condition')
    search_fields = ('manufacturer', 'model')
    exclude = ('category',)  # set automatically on save()
    inlines = [ProductImageInline]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'category', 'manufacturer', 'model', 'price', 'stock')
    list_filter = ('category',)
    search_fields = ('code', 'manufacturer', 'model')


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at')
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'date', 'total', 'status')
    list_filter = ('status',)
    inlines = [OrderItemInline]


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'position', 'is_active')
    list_editable = ('price', 'position', 'is_active')
