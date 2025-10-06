from django.contrib import admin
from .models import Warehouse, Stock, StockMovement, StockAlert

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'is_active')
    search_fields = ('name', 'location')
    list_filter = ('is_active',)

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'quantity', 'last_updated')
    list_filter = ('warehouse', 'product')
    search_fields = ('product__name',)

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        'product', 'movement_type', 'quantity', 'warehouse',
        'from_warehouse', 'to_warehouse', 'date', 'user'
    )
    list_filter = ('movement_type', 'warehouse', 'date')
    search_fields = ('product__name', 'source')

@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'message', 'created_at', 'is_resolved')
    list_filter = ('is_resolved', 'created_at')
    search_fields = ('product__name', 'message')
