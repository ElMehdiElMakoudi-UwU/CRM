from django import forms
from .models import PriceGrid, PriceRule

class PriceGridForm(forms.ModelForm):
    class Meta:
        model = PriceGrid
        fields = ['name', 'description', 'segment', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded px-3 py-2 border'}),
            'description': forms.Textarea(attrs={'class': 'w-full border-gray-300 rounded px-3 py-2 border', 'rows': 3}),
            'segment': forms.Select(attrs={'class': 'w-full border-gray-300 rounded px-3 py-2 border'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded border-gray-300'}),
        }

class PriceRuleForm(forms.ModelForm):
    class Meta:
        model = PriceRule
        fields = ['product', 'discount_type', 'discount_value', 'min_quantity', 'start_date', 'end_date', 'is_active']
        widgets = {
            'product': forms.Select(attrs={'class': 'w-full border-gray-300 rounded px-3 py-2 border'}),
            'discount_type': forms.Select(attrs={'class': 'w-full border-gray-300 rounded px-3 py-2 border'}),
            'discount_value': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded px-3 py-2 border'}),
            'min_quantity': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded px-3 py-2 border'}),
            'start_date': forms.DateInput(attrs={'class': 'w-full border-gray-300 rounded px-3 py-2 border', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'w-full border-gray-300 rounded px-3 py-2 border', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded border-gray-300'}),
        } 