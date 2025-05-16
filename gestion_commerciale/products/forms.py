from django import forms
from .models import Product, Category

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'reference', 'barcode', 'description', 'category', 'brand', 'unit',
            'supplier', 'purchase_price', 'selling_price', 'tax_rate',
            'expiration_date', 'is_featured',
            'default_warehouse', 'is_active', 'image'
        ]


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
