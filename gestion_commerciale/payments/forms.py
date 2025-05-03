# payments/forms.py
from django import forms
from .models import ClientPayment
from django.db.models import F, ExpressionWrapper, DecimalField


class ClientPaymentForm(forms.ModelForm):
    class Meta:
        model = ClientPayment
        fields = ['amount', 'method']
        widgets = {
            'method': forms.Select(attrs={"class": "form-select"}),
            'amount': forms.NumberInput(attrs={"class": "form-input"}),
        }

from django.forms import modelformset_factory
from .models import SalePayment

SalePaymentFormSet = modelformset_factory(
    SalePayment,
    fields=('sale', 'amount'),
    extra=0,
    can_delete=False
)


# payments/forms.py
from django import forms
from sales.models import Sale

class SaleAllocationForm(forms.Form):
    sale = forms.ModelChoiceField(queryset=Sale.objects.none(), widget=forms.Select(attrs={'class': 'form-select'}))
    amount = forms.DecimalField(decimal_places=2, max_digits=10, widget=forms.NumberInput(attrs={'class': 'form-input'}))

    def __init__(self, *args, client=None, **kwargs):
        super().__init__(*args, **kwargs)
        if client:
            self.fields['sale'].queryset = Sale.objects.filter(
                client=client, is_credit=True
            ).annotate(
                balance_due=ExpressionWrapper(
                    F('total_amount') - F('amount_paid'),
                    output_field=DecimalField()
                )
            ).filter(balance_due__gt=0)
