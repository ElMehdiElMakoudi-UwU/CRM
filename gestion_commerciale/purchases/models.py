from django.db import models
from django.utils import timezone
from datetime import timedelta

# Create your models here.

from datetime import timedelta
from django.utils import timezone

def default_due_date():
    return timezone.now().date() + timedelta(days=15)

class Purchase(models.Model):
    supplier = models.ForeignKey("suppliers.Supplier", on_delete=models.CASCADE, related_name="purchases")
    date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ("draft", "Brouillon"),
        ("ordered", "Commandé"),
        ("received", "Reçu"),
        ("cancelled", "Annulé"),
    ], default="ordered")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)
    due_date = models.DateField(default=default_due_date)
    
    def update_amount_paid(self):
        """Update the total amount paid for this purchase"""
        self.amount_paid = sum(p.amount for p in self.payments.all())
        self.save()

    @property
    def amount_due(self):
        return self.total_amount - self.amount_paid

    def is_overdue(self):
        return self.due_date and self.amount_due > 0 and self.due_date < timezone.now().date()

    def get_balance(self):
        return self.total_amount - self.amount_paid

    def __str__(self):
        return f"Achat #{self.id} - {self.supplier.name}"

class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class SupplierPayment(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name="payments")
    date = models.DateField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=[
        ("cash", "Espèces"),
        ("bank", "Virement bancaire"),
        ("check", "Chèque"),
        ("other", "Autre"),
    ])
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Paiement de {self.amount} DH pour {self.purchase}"

