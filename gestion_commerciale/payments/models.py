# payments/models.py
from django.db import models
from django.contrib.auth import get_user_model
from clients.models import Client

class ClientPayment(models.Model):
    PAYMENT_METHODS = [
        ('cash', 'Espèces'),
        ('card', 'Carte'),
        ('transfer', 'Virement'),
        ('mobile', 'Paiement mobile'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True)
    is_cancelled = models.BooleanField(default=False)  # ✅ ajout

    def __str__(self):
        return f"Paiement {self.amount} DH - {self.client.name}"

# payments/models.py
class SalePayment(models.Model):
    sale = models.ForeignKey('sales.Sale', on_delete=models.CASCADE, related_name='sale_payments')
    payment = models.ForeignKey(ClientPayment, on_delete=models.CASCADE, related_name='linked_sales')
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.amount} DH sur {self.sale}"
