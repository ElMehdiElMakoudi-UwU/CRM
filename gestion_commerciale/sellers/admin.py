from django.contrib import admin
from .models import Seller, SellerInventoryEntry

@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'phone', 'email', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code', 'phone', 'email')
    ordering = ('name',)

@admin.register(SellerInventoryEntry)
class SellerInventoryEntryAdmin(admin.ModelAdmin):
    list_display = ('seller', 'product', 'date', 'initial_stock', 'loaded_quantity', 
                   'returned_quantity', 'sold_quantity', 'amount')
    list_filter = ('date', 'seller', 'product')
    search_fields = ('seller__name', 'product__name')
    ordering = ('-date', 'seller__name')
    readonly_fields = ('total_assigned', 'sold_quantity', 'amount', 'created_by', 
                      'created_at', 'updated_at')
