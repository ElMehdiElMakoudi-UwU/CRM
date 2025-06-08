from django.contrib import admin
from .models import PriceGrid, PriceRule

class PriceRuleInline(admin.TabularInline):
    model = PriceRule
    extra = 1

@admin.register(PriceGrid)
class PriceGridAdmin(admin.ModelAdmin):
    list_display = ['name', 'segment', 'is_active', 'created_at']
    list_filter = ['is_active', 'segment']
    search_fields = ['name', 'description', 'segment__name']
    inlines = [PriceRuleInline]

@admin.register(PriceRule)
class PriceRuleAdmin(admin.ModelAdmin):
    list_display = ['price_grid', 'product', 'discount_type', 'discount_value', 'min_quantity', 'is_active']
    list_filter = ['price_grid', 'discount_type', 'is_active']
    search_fields = ['price_grid__name', 'product__name'] 