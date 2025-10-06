from django.db import models
from django.conf import settings
from products.models import Product
from django.utils.timezone import now

class Seller(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class SellerInventoryEntry(models.Model):
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name='inventory_entries')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    date = models.DateField()
    
    # Previous day's returns that are now in the vehicle
    initial_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # New products loaded today
    loaded_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Products returned at end of day
    returned_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Calculated field: initial_stock + loaded_quantity
    total_assigned = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Calculated field: total_assigned - returned_quantity
    sold_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Total amount based on sold quantity and product price
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_inventory_entries'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Calculate total assigned
        self.total_assigned = self.initial_stock + self.loaded_quantity
        
        # Calculate sold quantity
        self.sold_quantity = self.total_assigned - self.returned_quantity
        
        # Calculate amount
        self.amount = self.sold_quantity * self.product.selling_price
        
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ['seller', 'product', 'date']
        ordering = ['-date', 'seller', 'product']
        verbose_name = 'Seller Inventory Entry'
        verbose_name_plural = 'Seller Inventory Entries'

    def __str__(self):
        return f"{self.seller.name} - {self.product.name} - {self.date}"
