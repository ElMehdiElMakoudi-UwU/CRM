from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'client_name', 'order_date', 'status', 'total_amount')
    list_filter = ('status', 'created_at')
    search_fields = ('client_name', 'client_contact')
    inlines = [OrderItemInline]
    readonly_fields = ('created_at', 'updated_at')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'unit_price', 'subtotal')
    list_filter = ('order__status',)
    search_fields = ('order__client_name', 'product__name')
