from django.contrib import admin
from .models import Supplier, PurchaseOrder, PurchaseOrderItem

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'created_at')
    search_fields = ('name', 'email', 'phone')

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'order_date', 'received', 'total_amount')
    list_filter = ('received', 'order_date')
    search_fields = ('supplier__name',)
    inlines = [PurchaseOrderItemInline]

# Optionnel : si tu veux voir les items séparément dans l’admin
@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'unit_price', 'get_total_price')
    list_filter = ('order__supplier',)
    search_fields = ('product__name',)

    def get_total_price(self, obj):
        return obj.get_total_price()
    get_total_price.short_description = 'Total'
