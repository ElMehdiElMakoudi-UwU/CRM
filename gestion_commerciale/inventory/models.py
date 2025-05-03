from django.db import models
from django.utils import timezone
from products.models import Product

# Create your models here.


class Stock(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='stock')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    reorder_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    last_updated = models.DateTimeField(auto_now=True)

    def is_below_threshold(self):
        return self.quantity <= self.reorder_threshold

    def __str__(self):
        return f"{self.product.name} - {self.quantity} en stock"

class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('in', 'Entrée'),
        ('out', 'Sortie'),
        ('adjustment', 'Ajustement'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    source = models.CharField(max_length=100, blank=True)  # achat, vente, retour, etc.
    date = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.movement_type.upper()} - {self.product.name} - {self.quantity}"

class StockAlert(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='alerts')
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Alerte - {self.product.name}"

