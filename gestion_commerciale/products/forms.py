from django import forms
from .models import Product, Category
from inventory.models import Warehouse

class ProductForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Définir l'entrepôt par défaut si c'est un nouveau produit
        if not self.instance.pk:  # Si c'est un nouveau produit
            first_warehouse = Warehouse.objects.filter(is_active=True).first()
            if first_warehouse:
                self.initial['default_warehouse'] = first_warehouse.pk

    class Meta:
        model = Product
        fields = [
            'name', 'arabic_name', 'reference', 'barcode', 'description', 'category', 'brand', 'unit',
            'supplier', 'purchase_price', 'selling_price', 'tax_rate', 'reorder_threshold',
            'expiration_date', 'is_featured',
            'default_warehouse', 'is_active', 'image'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'arabic_name': forms.TextInput(attrs={
                'class': 'form-input text-right',
                'dir': 'rtl',
                'lang': 'ar'
            }),
            'reorder_threshold': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Seuil de réapprovisionnement'
            })
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']


class CSVImportForm(forms.Form):
    csv_file = forms.FileField(
        label='Sélectionnez un fichier CSV',
        help_text='Le fichier doit être au format CSV avec les colonnes suivantes : name, reference, description, purchase_price, selling_price, etc.'
    )
    encoding = forms.ChoiceField(
        choices=[
            ('utf-8', 'UTF-8'),
            ('iso-8859-1', 'ISO-8859-1'),
            ('cp1252', 'Windows-1252')
        ],
        initial='utf-8',
        label='Encodage du fichier'
    )
