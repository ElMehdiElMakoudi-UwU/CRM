from django import forms
from .models import Product, Category

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'reference', 'barcode', 'description', 'category', 'brand', 'unit',
            'supplier', 'purchase_price', 'selling_price', 'tax_rate', 'reorder_threshold',
            'expiration_date', 'is_featured',
            'default_warehouse', 'is_active', 'image'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'reorder_threshold': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Seuil de réapprovisionnement'
            })
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
