from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from clients.models import ClientSegment
from products.models import Product

class PriceGrid(models.Model):
    """
    Grille tarifaire qui peut être associée à un segment de clients
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
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
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Pourcentage'),
        ('fixed', 'Montant fixe'),
        ('fixed_price', 'Prix fixe'),
    ]

    price_grid = models.ForeignKey(
        PriceGrid,
        on_delete=models.CASCADE,
        related_name='price_rules'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='price_rules'
    )
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        default='percentage'
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    min_quantity = models.PositiveIntegerField(default=1)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.price_grid.name} - {self.product.name}"

    def get_final_price(self, base_price):
        """
        Calcule le prix final en fonction du type de remise
        """
        if self.discount_type == 'percentage':
            return base_price * (1 - self.discount_value / 100)
        elif self.discount_type == 'fixed':
            return max(base_price - self.discount_value, 0)
        else:  # fixed_price
            return self.discount_value

    class Meta:
        unique_together = ['price_grid', 'product', 'min_quantity']
        ordering = ['price_grid', 'product', 'min_quantity'] 