from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Product, Category
from .forms import ProductForm, CategoryForm, CSVImportForm
from django.db import models
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import csv
import io
from decimal import Decimal
from datetime import datetime

class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'

    def get_queryset(self):
        qs = Product.objects.select_related('category').all()
        q = self.request.GET.get('q', '').strip()
        cat = self.request.GET.get('category')

        if q:
            qs = qs.filter(models.Q(name__icontains=q) | models.Q(reference__icontains=q))
        if cat and cat.isdigit():
            qs = qs.filter(category_id=cat)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context

class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'products/product_form.html'
    success_url = reverse_lazy('products:product-list')


class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'products/product_form.html'
    success_url = reverse_lazy('products:product-list')


class ProductDeleteView(LoginRequiredMixin, DeleteView):
    model = Product
    template_name = 'products/product_confirm_delete.html'
    success_url = reverse_lazy('products:product-list')


class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'products/category_list.html'
    context_object_name = 'categories'


class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'products/category_form.html'
    success_url = reverse_lazy('products:category-list')


class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'products/category_form.html'
    success_url = reverse_lazy('products:category-list')


class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    template_name = 'products/category_confirm_delete.html'
    success_url = reverse_lazy('products:category-list')


from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .models import Product, Category

@require_GET
def search_products(request):
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category')

    products = Product.objects.select_related('category', 'default_warehouse').all()

    if query:
        products = products.filter(name__icontains=query)

    if category_id and category_id.isdigit():
        products = products.filter(category_id=category_id)

    results = []
    for product in products[:30]:
        results.append({
            'id': product.id,
            'name': product.name,
            'selling_price': float(product.selling_price),
            'category': product.category.name if product.category else '',
            'default_warehouse_id': product.default_warehouse.id if product.default_warehouse else None,
            'default_warehouse_name': product.default_warehouse.name if product.default_warehouse else None,
        })

    return JsonResponse(results, safe=False)

@login_required
def import_products_csv(request):
    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            encoding = form.cleaned_data['encoding']
            
            # Obtenir l'entrepôt par défaut
            from inventory.models import Warehouse
            default_warehouse = Warehouse.objects.filter(is_active=True).first()
            
            # Vérifier l'extension du fichier
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Le fichier doit être au format CSV')
                return redirect('products:import_products')

            try:
                # Lire le fichier CSV avec gestion du BOM
                csv_data = csv_file.read()
                if csv_data.startswith(b'\xef\xbb\xbf'):  # UTF-8 BOM
                    csv_data = csv_data[3:]
                csv_text = csv_data.decode(encoding)
                
                # Détecter le délimiteur (semicolon ou comma)
                first_line = csv_text.split('\n')[0]
                delimiter = ';' if ';' in first_line else ','
                
                # Nettoyer les en-têtes
                headers = [h.strip() for h in first_line.split(delimiter)]
                print(f"En-têtes détectés: {headers}")  # Debug log
                print(f"Délimiteur détecté: {delimiter}")  # Debug log
                
                io_string = io.StringIO(csv_text)
                reader = csv.DictReader(io_string, delimiter=delimiter)
                
                # Normaliser les noms de colonnes (supprimer les espaces)
                reader.fieldnames = [field.strip() for field in reader.fieldnames] if reader.fieldnames else []
                
                # Vérifier les colonnes requises
                required_fields = ['name', 'reference', 'purchase_price', 'selling_price']
                missing_fields = [field for field in required_fields if field not in reader.fieldnames]
                
                if missing_fields:
                    messages.error(request, f'Colonnes manquantes dans le fichier CSV: {", ".join(missing_fields)}')
                    return redirect('products:import_products')
                
                success_count = 0
                error_count = 0
                errors = []

                for row in reader:
                    try:
                        # Vérifier les champs obligatoires
                        if not row.get('name') or not row.get('reference'):
                            raise ValueError("Le nom et la référence sont obligatoires")

                        # Nettoyer et convertir les données
                        product_data = {
                            'name': row.get('name', '').strip(),
                            'arabic_name': row.get('arabic_name', '').strip(),
                            'reference': row.get('reference', '').strip(),
                            'description': row.get('description', '').strip(),
                            'purchase_price': Decimal(row.get('purchase_price', '0').replace(',', '.').strip()),
                            'selling_price': Decimal(row.get('selling_price', '0').replace(',', '.').strip()),
                            'tax_rate': Decimal(row.get('tax_rate', '0').replace(',', '.').strip()),
                            'brand': row.get('brand', '').strip(),
                            'unit': row.get('unit', 'unit').strip(),
                            'is_active': row.get('is_active', 'True').lower() == 'true',
                            'default_warehouse': default_warehouse
                        }

                        # Ne pas inclure le code-barres s'il est vide
                        barcode = row.get('barcode', '').strip()
                        if barcode:
                            product_data['barcode'] = barcode

                        # Gérer la catégorie
                        category_name = row.get('category', '').strip()
                        if category_name:
                            category, _ = Category.objects.get_or_create(name=category_name)
                            product_data['category'] = category

                        # Gérer le fournisseur
                        supplier_name = row.get('supplier', '').strip()
                        if supplier_name:
                            from suppliers.models import Supplier
                            supplier, _ = Supplier.objects.get_or_create(name=supplier_name)
                            product_data['supplier'] = supplier

                        # Vérifier si le produit existe déjà
                        try:
                            existing_product = Product.objects.get(reference=product_data['reference'])
                            # Mettre à jour le produit existant
                            for key, value in product_data.items():
                                setattr(existing_product, key, value)
                            existing_product.save()
                        except Product.DoesNotExist:
                            # Créer un nouveau produit
                            Product.objects.create(**product_data)

                        success_count += 1

                    except Exception as e:
                        error_count += 1
                        errors.append(f"Ligne {reader.line_num}: {str(e)}")
                        print(f"Erreur d'importation à la ligne {reader.line_num}: {str(e)}")  # Debug log

                # Afficher le résultat
                if success_count > 0:
                    messages.success(request, f'{success_count} produits ont été importés avec succès.')
                if error_count > 0:
                    messages.warning(request, f'{error_count} erreurs rencontrées lors de l\'importation.')
                    for error in errors:
                        messages.error(request, error)

            except Exception as e:
                messages.error(request, f'Erreur lors de la lecture du fichier: {str(e)}')
                print(f"Erreur générale lors de l'importation: {str(e)}")  # Debug log
                return redirect('products:import_products')

            return redirect('products:product-list')
    else:
        form = CSVImportForm()

    return render(request, 'products/import_products.html', {'form': form})


@login_required
def download_csv_template(request):
    """Download a CSV template for importing products"""
    # Create the HttpResponse object with the appropriate CSV header
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="products_template.csv"'
    
    # Add BOM for Excel compatibility
    response.write('\ufeff')
    
    # Create a CSV writer with semicolon delimiter (matches import format)
    writer = csv.writer(response, delimiter=';')
    
    # Write the header row with all possible fields
    writer.writerow([
        'name',
        'reference',
        'arabic_name',
        'description',
        'barcode',
        'category',
        'brand',
        'unit',
        'supplier',
        'purchase_price',
        'selling_price',
        'tax_rate',
        'is_active',
    ])
    
    # Write a sample row with example values
    writer.writerow([
        'Exemple Produit',
        'REF001',
        'منتج مثال',
        'Description du produit exemple',
        '1234567890123',
        'Catégorie Exemple',
        'Marque Exemple',
        'unit',
        'Fournisseur Exemple',
        '100.00',
        '150.00',
        '20.00',
        'True',
    ])
    
    return response


@login_required
def export_products_csv(request):
    """Export all products and their data as CSV"""
    # Create the HttpResponse object with the appropriate CSV header
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="products_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    # Add BOM for Excel compatibility
    response.write('\ufeff')
    
    # Create a CSV writer
    writer = csv.writer(response)
    
    # Write the header row
    writer.writerow([
        'ID',
        'Nom',
        'Nom en arabe',
        'Référence',
        'Code-barres',
        'Description',
        'Catégorie',
        'Marque',
        'Unité',
        'Fournisseur',
        'Prix d\'achat',
        'Prix de vente',
        'Taux de TVA (%)',
        'Seuil de réapprovisionnement',
        'Date d\'expiration',
        'Produit en vedette',
        'Entrepôt par défaut',
        'Actif',
        'Date de création',
        'Date de mise à jour',
    ])
    
    # Get all products with related data
    products = Product.objects.select_related('category', 'supplier', 'default_warehouse').all().order_by('id')
    
    # Write data rows
    for product in products:
        writer.writerow([
            product.id,
            product.name,
            product.arabic_name or '',
            product.reference,
            product.barcode or '',
            product.description or '',
            product.category.name if product.category else '',
            product.brand or '',
            product.get_unit_display() if product.unit else '',
            product.supplier.name if product.supplier else '',
            str(product.purchase_price),
            str(product.selling_price),
            str(product.tax_rate),
            str(product.reorder_threshold),
            product.expiration_date.strftime('%Y-%m-%d') if product.expiration_date else '',
            'Oui' if product.is_featured else 'Non',
            product.default_warehouse.name if product.default_warehouse else '',
            'Oui' if product.is_active else 'Non',
            product.created_at.strftime('%Y-%m-%d %H:%M:%S') if product.created_at else '',
            product.updated_at.strftime('%Y-%m-%d %H:%M:%S') if product.updated_at else '',
        ])
    
    return response
