from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    UNIT_CHOICES = [
        ('unit', 'Unité'),
        ('kg', 'Kilogramme'),
        ('l', 'Litre'),
        ('box', 'Boîte'),
    ]

    name = models.CharField(max_length=200)
    arabic_name = models.CharField("Nom en arabe", max_length=200, blank=True, null=True)
    reference = models.CharField(max_length=100, unique=True)
    barcode = models.CharField("Code-barres", max_length=100, blank=True, null=True, unique=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    brand = models.CharField(max_length=100, blank=True)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='unit')

    supplier = models.ForeignKey('suppliers.Supplier', on_delete=models.SET_NULL, null=True, blank=True)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    reorder_threshold = models.DecimalField("Seuil de réapprovisionnement", max_digits=10, decimal_places=2, default=0.00)

    expiration_date = models.DateField("Date d'expiration", blank=True, null=True)
    is_featured = models.BooleanField("Produit en vedette", default=False)

    default_warehouse = models.ForeignKey(
        'inventory.Warehouse',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='default_products'
    )

    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def price_with_tax(self):
        return self.selling_price * (1 + self.tax_rate / 100)

    @property
    def current_stock(self):
        """Get the current stock quantity from the default warehouse."""
        from inventory.models import Stock
        if self.default_warehouse:
            stock = Stock.objects.filter(product=self, warehouse=self.default_warehouse).first()
            return stock.quantity if stock else 0
        return 0

    @current_stock.setter
    def current_stock(self, value):
        """This is a no-op setter to prevent AttributeError when Django tries to set the property."""
        pass  # We don't actually want to set anything here

    @property
    def total_stock(self):
        from inventory.models import Stock
        stock_qs = Stock.objects.filter(product=self)
        return sum([s.quantity for s in stock_qs])
