from django import forms
from .models import Client, ClientSegment

class ClientSegmentForm(forms.ModelForm):
    class Meta:
        model = ClientSegment
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input'}),
            'description': forms.Textarea(attrs={'class': 'textarea', 'rows': 3}),
        }

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'phone', 'email', 'address', 'segment','alert_threshold']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input'}),
            'phone': forms.TextInput(attrs={'class': 'input'}),
            'email': forms.EmailInput(attrs={'class': 'input'}),
            'address': forms.Textarea(attrs={'class': 'textarea', 'rows': 3}),
            'segment': forms.Select(attrs={'class': 'select'}),
            # 'balance': forms.NumberInput(attrs={'class': 'input'}),
            'alert_threshold': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Seuil alerte en DH'
            }),
        }
    
