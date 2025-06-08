from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from clients.models import ClientSegment
from products.models import Product

class PriceGrid(models.Model):
    """
    Grille tarifaire qui peut être associée à un segment de clients
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    segment = models.ForeignKey(
        ClientSegment,
        on_delete=models.CASCADE,
        related_name='price_grids'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.segment.name}"

    class Meta:
        ordering = ['name']


class PriceRule(models.Model):
    """
    Règle de prix spécifique pour un produit dans une grille tarifaire
    """
    DISCOUNT_TYPES = [
        ('percentage', 'Pourcentage'),
        ('fixed', 'Montant fixe'),
        ('fixed_price', 'Prix fixe'),
    ]

    price_grid = models.ForeignKey(
        PriceGrid,
        on_delete=models.CASCADE,
        related_name='rules'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='price_rules'
    )
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPES,
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    min_quantity = models.PositiveIntegerField(default=1)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.price_grid.name} - {self.product.name} ({self.get_discount_type_display()})"

    def get_final_price(self, base_price):
        """
        Calcule le prix final en fonction du type de remise
        """
        if self.discount_type == 'percentage':
            return base_price * (1 - self.discount_value / 100)
        elif self.discount_type == 'fixed':
            return max(base_price - self.discount_value, Decimal('0.00'))
        elif self.discount_type == 'fixed_price':
            return self.discount_value
        return base_price

    def save(self, *args, **kwargs):
        if not self.pk:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-min_quantity']  # Higher quantities first 