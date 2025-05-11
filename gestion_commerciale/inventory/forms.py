from django import forms
from .models import Stock, StockMovement, Warehouse

class StockForm(forms.ModelForm):
    class Meta:
        model = Stock
        fields = ['product', 'warehouse', 'quantity', 'reorder_threshold']

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
