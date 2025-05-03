from django import forms
from .models import StockMovement  # ← import corrigé

class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ['product', 'movement_type', 'quantity', 'source']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'w-full p-2 border rounded-lg'
            }),
            'movement_type': forms.Select(attrs={
                'class': 'w-full p-2 border rounded-lg'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded-lg',
                'step': '0.01',
                'min': '0'
            }),
            'source': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded-lg',
                'placeholder': 'Achat, vente, retour, etc.'
            }),
        }
