from django import forms
from .models import Sale, SaleItem, Payment
from django.forms.models import inlineformset_factory
from clients.models import Client
from inventory.models import Warehouse

class SaleForm(forms.ModelForm):
    client = forms.ModelChoiceField(
        queryset=Client.objects.all(),
        required=False,
        empty_label="Client anonyme"
    )
    
    class Meta:
        model = Sale
        fields = ['client', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'w-full'}),
        }

class SaleItemForm(forms.ModelForm):
    class Meta:
        model = SaleItem
        fields = ['product', 'quantity', 'unit_price']
        widgets = {
            'product': forms.Select(attrs={'class': 'w-full'}),
            'quantity': forms.NumberInput(attrs={'class': 'w-full'}),
            'unit_price': forms.NumberInput(attrs={'class': 'w-full', 'readonly': 'readonly'}),
        }


SaleItemFormSet = inlineformset_factory(
    Sale, SaleItem, form=SaleItemForm,
    fields=['product', 'quantity', 'unit_price'],
    extra=1, can_delete=True
)

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'method']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'w-full'}),
            'method': forms.Select(attrs={'class': 'w-full'}),
        }
