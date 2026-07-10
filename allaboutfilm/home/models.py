from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------
class User(AbstractUser):
    """Custom user model. Extends Django's AbstractUser (username, email,
    first_name, last_name, hashed password). Authorization is handled through
    Django Groups/Permissions (Customer, Employee, Manager groups)."""

    def __str__(self):
        return self.username


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------
class Product(models.Model):
    """Base catalog entry. Every sellable thing is a Product; Camera, Lens and
    Film extend it with their category-specific fields (multi-table
    inheritance). Cart and order items point at Product, so they don't care
    which category they hold."""

    class Category(models.TextChoices):
        CAMERA = 'CAMERA', 'Camera'
        LENS = 'LENS', 'Lens'
        FILM = 'FILM', 'Film'

    # Human-readable, category-prefixed primary key: C000 / L000 / F000 ...
    code = models.CharField(max_length=10, primary_key=True, editable=False)
    category = models.CharField(max_length=10, choices=Category.choices)
    manufacturer = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # Units available: 0 or 1 for a unique camera/lens, N for stocked film.
    stock = models.PositiveIntegerField(default=1)

    _CODE_PREFIX = {'CAMERA': 'C', 'LENS': 'L', 'FILM': 'F'}

    def save(self, *args, **kwargs):
        # Generate the next code for this category the first time we save.
        if not self.code:
            prefix = self._CODE_PREFIX[self.category]
            last = (Product.objects
                    .filter(code__startswith=prefix)
                    .order_by('code')
                    .last())
            nxt = int(last.code[1:]) + 1 if last else 0
            self.code = f"{prefix}{nxt:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} — {self.manufacturer} {self.model}"


class GearCondition(models.TextChoices):
    MINT = 'MINT', 'Mint'
    EXCELLENT = 'EXCELLENT', 'Excellent'
    GOOD = 'GOOD', 'Good'
    FAIR = 'FAIR', 'Fair'
    POOR = 'POOR', 'Poor'


class Camera(Product):
    class Type(models.TextChoices):
        SLR = 'SLR', 'SLR'
        RANGEFINDER = 'RANGEFINDER', 'Rangefinder'
        MEDIUM_FORMAT = 'MEDIUM_FORMAT', 'Medium Format'
        LARGE_FORMAT = 'LARGE_FORMAT', 'Large Format'

    type = models.CharField(max_length=20, choices=Type.choices)
    serial_number = models.CharField(max_length=50, unique=True)
    condition = models.CharField(max_length=20, choices=GearCondition.choices)

    def save(self, *args, **kwargs):
        self.category = Product.Category.CAMERA
        super().save(*args, **kwargs)


class Lens(Product):
    class Type(models.TextChoices):
        SLR = 'SLR', 'SLR'
        RANGEFINDER = 'RANGEFINDER', 'Rangefinder'
        MEDIUM_FORMAT = 'MEDIUM_FORMAT', 'Medium Format'
        LARGE_FORMAT = 'LARGE_FORMAT', 'Large Format'
        ENLARGER = 'ENLARGER', 'Enlarger'

    type = models.CharField(max_length=20, choices=Type.choices)
    serial_number = models.CharField(max_length=50, unique=True)
    condition = models.CharField(max_length=20, choices=GearCondition.choices)

    class Meta:
        verbose_name_plural = 'Lenses'

    def save(self, *args, **kwargs):
        self.category = Product.Category.LENS
        super().save(*args, **kwargs)


class Film(Product):
    class Format(models.TextChoices):
        MM35 = '35MM', '35mm'
        MM120 = '120', '120'
        INSTANT = 'INSTANT', 'Instant'
        SHEET = 'SHEET', 'Sheet'

    class FilmType(models.TextChoices):
        COLOR = 'COLOR', 'Color'
        BW = 'BW', 'B/W'

    class Condition(models.TextChoices):
        NEW = 'NEW', 'New'
        EXPIRED = 'EXPIRED', 'Expired'

    format = models.CharField(max_length=10, choices=Format.choices)
    film_type = models.CharField(max_length=10, choices=FilmType.choices)
    iso = models.PositiveIntegerField()
    condition = models.CharField(
        max_length=10, choices=Condition.choices, default=Condition.NEW
    )

    def save(self, *args, **kwargs):
        self.category = Product.Category.FILM
        super().save(*args, **kwargs)


class ProductImage(models.Model):
    """Gallery images for a product (feeds the 4-slide carousel on the front
    end). One product -> many images, ordered by `position`."""

    product = models.ForeignKey(
        Product, related_name='images', on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to='products/')
    position = models.PositiveIntegerField(default=0)
    alt_text = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ['position']

    def __str__(self):
        return f"Image {self.position} for {self.product_id}"


# ---------------------------------------------------------------------------
# Commerce
# ---------------------------------------------------------------------------
class Cart(models.Model):
    """One cart per user."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart of {self.user}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        # A product appears at most once per cart (quantity handles the rest).
        unique_together = [['cart', 'product']]

    def __str__(self):
        return f"{self.quantity} x {self.product_id} in {self.cart_id}"


class Order(models.Model):
    class Status(models.TextChoices):
        PROCESSING = 'PROCESSING', 'Processing'
        SHIPPED = 'SHIPPED', 'Shipped'
        COMPLETED = 'COMPLETED', 'Completed'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders'
    )
    date = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PROCESSING
    )

    def __str__(self):
        return f"Order #{self.pk} by {self.user} ({self.get_status_display()})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    # PROTECT: a product that has been ordered can't be deleted, so order
    # history stays intact.
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    # Price snapshot at the time of purchase (prices change over time).
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product_id} in order #{self.order_id}"
