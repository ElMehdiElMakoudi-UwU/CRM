from django.db import models
from django.conf import settings
from products.models import Product
from clients.models import Client
from inventory.models import StockMovement

class Sale(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_credit = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    
    def get_balance_due(self):
        return self.total_amount - self.amount_paid

    def __str__(self):
        return f"Vente #{self.id} - {self.client or 'Client anonyme'}"

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def total_price(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

class Payment(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='payments')
    date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=50, choices=[
        ('cash', 'Espèces'),
        ('card', 'Carte'),
        ('transfer', 'Virement'),
        ('mobile', 'Paiement mobile'),
    ])

    def __str__(self):
        return f"{self.amount} MAD le {self.date.date()}"
