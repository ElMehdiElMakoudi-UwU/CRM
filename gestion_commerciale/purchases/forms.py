from django import forms
from .models import Purchase, PurchaseItem, SupplierPayment
from django.forms import inlineformset_factory

class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ["supplier", "status", "notes"]

class PurchaseItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseItem
        fields = ["product", "quantity", "unit_price"]

PurchaseItemFormSet = inlineformset_factory(
    Purchase, PurchaseItem, form=PurchaseItemForm,
    fields=["product", "quantity", "unit_price"],
    extra=1, can_delete=True
)

class SupplierPaymentForm(forms.ModelForm):
    class Meta:
        model = SupplierPayment
        fields = ["amount", "payment_method", "note"]
