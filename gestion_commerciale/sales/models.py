from django.db import models
from django.conf import settings
from products.models import Product
from clients.models import Client
from inventory.models import StockMovement, Warehouse, Stock
from comptabilite.services import ComptabiliteService
from django.contrib.auth import get_user_model
from decimal import Decimal

def get_default_warehouse():
    return Warehouse.objects.filter(is_active=True).first()

class Sale(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)
    warehouse = models.ForeignKey(
        Warehouse, 
        on_delete=models.PROTECT, 
        related_name='sales',
        null=True,  # Temporairement nullable
        blank=True  # Temporairement optional
    )
    date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_credit = models.BooleanField(default=False, blank=True)
    notes = models.TextField(blank=True, null=True)
    ecriture_generee = models.BooleanField(default=False)
    
    def get_balance_due(self):
        return self.total_amount - self.amount_paid
    
    def save(self, *args, **kwargs):
        # Détection automatique du crédit
        self.is_credit = self.amount_paid < self.total_amount
        
        # Si pas d'entrepôt spécifié, utiliser le premier entrepôt actif
        if not self.warehouse:
            self.warehouse = Warehouse.objects.filter(is_active=True).first()
        
        # Sauvegarde de la vente
        super().save(*args, **kwargs)
        
        # Génération de l'écriture comptable si pas encore générée
        if not self.ecriture_generee and self.user:
            try:
                ComptabiliteService.generer_ecriture_vente(self, self.user)
                self.ecriture_generee = True
                self.save(update_fields=['ecriture_generee'])
            except ValueError as e:
                # Log l'erreur mais ne bloque pas la sauvegarde
                print(f"Erreur lors de la génération de l'écriture comptable : {str(e)}")

    def __str__(self):
        return f"Vente #{self.id} - {self.client or 'Client anonyme'}"

    def get_remaining_amount(self):
        """Calculate remaining amount to be paid"""
        return self.total_amount - self.amount_paid

    @property
    def is_fully_paid(self):
        """Check if sale is fully paid"""
        return self.get_remaining_amount() <= 0

    def update_payment_status(self):
        """Update payment status based on payments"""
        total_paid = self.payments.aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
        self.amount_paid = total_paid
        self.is_credit = total_paid < self.total_amount
        self.save()

    @property
    def total_amount_ttc(self):
        total = 0
        for item in self.items.all():
            total += float(item.unit_price) * float(1 + (item.product.tax_rate or 0) / 100) * float(item.quantity)
        return round(total, 2)

    @property
    def balance_due_ttc(self):
        return round(self.total_amount_ttc - float(self.amount_paid), 2)

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

    def save(self, *args, **kwargs):
        if not self.pk:  # Only check on creation
            # Check if there's enough stock in the product's default warehouse
            from inventory.models import Stock
            if not self.product.default_warehouse:
                raise ValueError("Le produit n'a pas d'entrepôt par défaut défini")
                
            stock = Stock.objects.filter(
                product=self.product,
                warehouse=self.product.default_warehouse
            ).first()
            current_stock = stock.quantity if stock else 0
            if current_stock < self.quantity:
                raise ValueError(f"Stock insuffisant dans l'entrepôt {self.product.default_warehouse.name}. Stock disponible: {current_stock}")
        super().save(*args, **kwargs)

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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.sale.update_payment_status()
