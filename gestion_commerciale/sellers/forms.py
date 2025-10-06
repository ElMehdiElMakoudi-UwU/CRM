from django import forms
from .models import Seller, SellerInventoryEntry
from products.models import Product
from inventory.models import Stock, Warehouse

class SellerForm(forms.ModelForm):
    class Meta:
        model = Seller
        fields = ['name', 'code', 'phone', 'email', 'address', 'is_active']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }

class LoadInventoryForm(forms.Form):
    seller = forms.ModelChoiceField(
        queryset=Seller.objects.filter(is_active=True),
        empty_label=None
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Récupérer le dépôt actif
        active_warehouse = Warehouse.objects.filter(is_active=True).first()
        
        # Add dynamic fields for each product
        for product in Product.objects.filter(is_active=True):
            # Récupérer le stock du dépôt actif
            stock = Stock.objects.filter(
                product=product,
                warehouse=active_warehouse
            ).first()
            current_stock = stock.quantity if stock else 0
            
            field = forms.DecimalField(
                label=f'Charger {product.name}',
                required=False,
                min_value=0,
                initial=0,
                widget=forms.NumberInput(attrs={
                    'product': {
                        'id': product.id,
                        'name': product.name,
                        'current_stock': current_stock,
                        'selling_price': float(product.selling_price),
                        'unit': product.get_unit_display()
                    },
                    'class': 'form-control',
                    'min': 0,
                    'max': current_stock
                })
            )
            self.fields[f'load_{product.id}'] = field

class UnloadInventoryForm(forms.Form):
    seller = forms.ModelChoiceField(
        queryset=Seller.objects.filter(is_active=True),
        empty_label=None
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add dynamic fields for each product
        for product in Product.objects.filter(is_active=True):
            self.fields[f'return_{product.id}'] = forms.DecimalField(
                label=f'Retour {product.name}',
                required=False,
                min_value=0,
                initial=0
            ) 