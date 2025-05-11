from django.contrib import admin
from .models import Purchase, PurchaseItem, SupplierPayment

class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 1

class SupplierPaymentInline(admin.TabularInline):
    model = SupplierPayment
    extra = 0

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("id", "supplier", "date", "status", "total_amount", "amount_paid", "get_balance")
    list_filter = ("status", "date", "supplier")
    search_fields = ("supplier__name",)
    inlines = [PurchaseItemInline, SupplierPaymentInline]

    def get_balance(self, obj):
        return obj.get_balance()
    get_balance.short_description = "Solde dû"

@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):
    list_display = ("purchase", "product", "quantity", "unit_price", "subtotal")
    list_filter = ("product",)
    search_fields = ("product__name",)

@admin.register(SupplierPayment)
class SupplierPaymentAdmin(admin.ModelAdmin):
    list_display = ("purchase", "amount", "payment_method", "date")
    list_filter = ("payment_method", "date")
    search_fields = ("purchase__supplier__name",)
