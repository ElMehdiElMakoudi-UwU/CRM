from django.contrib import admin
from .models import Sale, SaleItem, Payment

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'date', 'total_amount', 'amount_paid', 'is_credit')
    list_filter = ('is_credit', 'date')
    search_fields = ('client__name',)
    inlines = [SaleItemInline, PaymentInline]

@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('sale', 'product', 'quantity', 'unit_price')
    list_filter = ('product',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('sale', 'amount', 'method', 'date')
    list_filter = ('method', 'date')
