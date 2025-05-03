from django import forms
from .models import Product, Category

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'reference', 'description', 'category', 'brand', 'unit',
            'supplier', 'purchase_price', 'selling_price', 'tax_rate',
            'is_active', 'image'
        ]


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']

