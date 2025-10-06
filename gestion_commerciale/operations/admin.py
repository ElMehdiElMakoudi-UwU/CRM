# Register your models here.
from django.contrib import admin
from .models import Seller, SellerProductDayEntry

# --- Configuration for Seller ---
@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    """Admin configuration for the Seller model."""
    list_display = ('name', 'is_active')
    search_fields = ('name',)
    list_filter = ('is_active',)

# --- Configuration for Product ---
class ProductAdmin(admin.ModelAdmin):
    """Admin configuration for the Product model."""
    list_display = ('name', 'quantity', 'selling_price')
    search_fields = ('name',)
    # Allow quick editing of quantity and price directly in the list view
    list_editable = ('quantity', 'selling_price')
    
# --- Configuration for Daily Inventory Entry ---
@admin.register(SellerProductDayEntry)
class SellerProductDayEntryAdmin(admin.ModelAdmin):
    """Admin configuration for the daily log entries."""
    
    # Fields displayed in the list view
    list_display = (
        'date', 'seller', 'product', 
        'voiture', 'sortie', 'total_loaded', 
        'retour', 'vendu', 'amount'
    )
    
    # Fields used for filtering the results
    list_filter = ('date', 'seller', 'product')
    
    # Fields that can be searched
    search_fields = ('seller__name', 'product__name')
    
    # Group fields in the detail view for better organization
    fieldsets = (
        ('Identification', {
            'fields': ('date', 'seller', 'product'),
        }),
        ('Mouvements d\'Inventaire', {
            'fields': ('voiture', 'sortie', 'total_loaded', 'retour'),
        }),
        ('Ventes & Finances (Calculé)', {
            'fields': ('vendu', 'amount'),
        }),
    )

    # Make the calculated fields read-only
    readonly_fields = ('total_loaded', 'vendu', 'amount')
