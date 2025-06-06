from django import forms
from .models import Stock, StockMovement, Warehouse

class StockForm(forms.ModelForm):
    class Meta:
        model = Stock
        fields = ['product', 'warehouse', 'quantity']

class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = [
            'product',
            'movement_type',
            'quantity',
            'warehouse',
            'from_warehouse',
            'to_warehouse',
            'source',
            'user'
        ]

    def clean(self):
        cleaned_data = super().clean()
        movement_type = cleaned_data.get('movement_type')
        from_warehouse = cleaned_data.get('from_warehouse')
        to_warehouse = cleaned_data.get('to_warehouse')

        if movement_type == 'transfer':
            if not from_warehouse or not to_warehouse:
                raise forms.ValidationError(
                    "Pour un transfert, il faut spécifier les entrepôts source et destination."
                )
            if from_warehouse == to_warehouse:
                raise forms.ValidationError(
                    "Les entrepôts source et destination doivent être différents."
                )

from django import forms
from inventory.models import StockMovement, Warehouse, Product

class StockTransferForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ['product', 'from_warehouse', 'to_warehouse', 'quantity', 'source']
        labels = {
            'product': 'Produit',
            'from_warehouse': 'Dépôt de départ',
            'to_warehouse': 'Dépôt de destination',
            'quantity': 'Quantité à transférer',
            'source': 'Référence ou remarque (optionnel)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Affichage plus lisible
        self.fields['product'].widget.attrs.update({'class': 'p-3 rounded w-full'})
        self.fields['from_warehouse'].widget.attrs.update({'class': 'p-3 rounded w-full'})
        self.fields['to_warehouse'].widget.attrs.update({'class': 'p-3 rounded w-full'})
        self.fields['quantity'].widget.attrs.update({'class': 'p-3 rounded w-full', 'placeholder': 'Quantité'})
        self.fields['source'].widget.attrs.update({'class': 'p-3 rounded w-full', 'placeholder': 'ex: Rééquilibrage'})

    def clean(self):
        cleaned_data = super().clean()
        from_warehouse = cleaned_data.get('from_warehouse')
        to_warehouse = cleaned_data.get('to_warehouse')
        if from_warehouse and to_warehouse and from_warehouse == to_warehouse:
            raise forms.ValidationError("Les deux entrepôts doivent être différents.")
