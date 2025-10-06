from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.timezone import now
from datetime import timedelta
from django.db.models import F
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa

from .models import Seller, SellerInventoryEntry
from .forms import LoadInventoryForm, UnloadInventoryForm
from products.models import Product
from inventory.models import Stock, StockMovement, Warehouse

@login_required
def load_inventory(request):
    """Vue pour charger l'inventaire d'un vendeur."""
    
    if request.method == 'POST':
        form = LoadInventoryForm(request.POST)
        if form.is_valid():
            seller = form.cleaned_data['seller']
            selected_date = form.cleaned_data['date']
            
            # Récupérer la date d'hier
            yesterday = selected_date - timedelta(days=1)
            
            # Traiter chaque produit
            entries = []
            default_warehouse = Warehouse.objects.filter(is_active=True).first()
            
            for product in Product.objects.filter(is_active=True):
                # Récupérer la quantité à charger depuis le formulaire
                load_qty = form.cleaned_data.get(f'load_{product.id}', 0)
                
                if load_qty > 0:
                    # Vérifier le stock disponible
                    stock = Stock.objects.filter(
                        product=product,
                        warehouse=default_warehouse
                    ).first()
                    
                    if not stock or stock.quantity < load_qty:
                        messages.error(
                            request,
                            f"Stock insuffisant pour {product.name}. "
                            f"Disponible: {stock.quantity if stock else 0}"
                        )
                        continue
                    
                    # Récupérer la quantité retournée hier (si elle existe)
                    yesterday_entry = SellerInventoryEntry.objects.filter(
                        seller=seller,
                        product=product,
                        date=yesterday
                    ).first()
                    
                    initial_stock = yesterday_entry.returned_quantity if yesterday_entry else 0
                    
                    # Créer ou mettre à jour l'entrée d'aujourd'hui
                    entry, _ = SellerInventoryEntry.objects.update_or_create(
                        seller=seller,
                        product=product,
                        date=selected_date,
                        defaults={
                            'initial_stock': initial_stock,
                            'loaded_quantity': load_qty,
                            'returned_quantity': 0,  # Sera mis à jour lors du déchargement
                            'created_by': request.user
                        }
                    )
                    
                    # Créer le mouvement de stock
                    StockMovement.objects.create(
                        product=product,
                        warehouse=default_warehouse,
                        movement_type='out',
                        quantity=load_qty,
                        source=f'Chargement vendeur: {seller.name}',
                        user=request.user
                    )
                    
                    # Mettre à jour le stock
                    stock.quantity = F('quantity') - load_qty
                    stock.save()
                    
                    entries.append(entry)
            
            if entries:
                # Générer le PDF
                template = get_template('sellers/load_report.html')
                html = template.render({
                    'seller': seller,
                    'date': selected_date,
                    'entries': entries,
                })
                
                response = HttpResponse(content_type='application/pdf')
                response['Content-Disposition'] = f'filename="Chargement-{seller.name}-{selected_date}.pdf"'
                pisa.CreatePDF(html, dest=response)
                return response
            
            messages.success(request, "Chargement d'inventaire enregistré avec succès.")
            return redirect('sellers:load_inventory')
    else:
        form = LoadInventoryForm(initial={'date': now().date()})
    
    return render(request, 'sellers/load_inventory.html', {
        'form': form,
    })

@login_required
def unload_inventory(request):
    """Vue pour décharger l'inventaire d'un vendeur."""
    
    if request.method == 'POST':
        form = UnloadInventoryForm(request.POST)
        if form.is_valid():
            seller = form.cleaned_data['seller']
            selected_date = form.cleaned_data['date']
            
            entries = []
            default_warehouse = Warehouse.objects.filter(is_active=True).first()
            
            for product in Product.objects.filter(is_active=True):
                return_qty = form.cleaned_data.get(f'return_{product.id}', 0)
                
                if return_qty >= 0:  # Permettre les retours à 0 pour mettre à jour les ventes
                    entry = SellerInventoryEntry.objects.filter(
                        seller=seller,
                        product=product,
                        date=selected_date
                    ).first()
                    
                    if entry:
                        # Stocker la quantité vendue précédente pour l'ajustement du stock
                        previous_sold = entry.sold_quantity
                        
                        # Mettre à jour la quantité retournée
                        entry.returned_quantity = return_qty
                        entry.save()  # Cela recalculera la quantité vendue
                        
                        # Ajuster le stock global basé sur la différence des ventes
                        sales_difference = entry.sold_quantity - previous_sold
                        
                        if sales_difference != 0:
                            # Mettre à jour le stock
                            stock = Stock.objects.filter(
                                product=product,
                                warehouse=default_warehouse
                            ).first()
                            
                            if not stock:
                                stock = Stock.objects.create(
                                    product=product,
                                    warehouse=default_warehouse,
                                    quantity=0
                                )
                            
                            # Créer le mouvement de stock pour les ventes
                            StockMovement.objects.create(
                                product=product,
                                warehouse=default_warehouse,
                                movement_type='out' if sales_difference > 0 else 'in',
                                quantity=abs(sales_difference),
                                source=f'Déchargement vendeur: {seller.name}',
                                user=request.user
                            )
                            
                            # Mettre à jour le stock
                            stock.quantity = F('quantity') - sales_difference
                            stock.save()
                        
                        entries.append(entry)
            
            if entries:
                # Générer le PDF
                template = get_template('sellers/unload_report.html')
                html = template.render({
                    'seller': seller,
                    'date': selected_date,
                    'entries': entries,
                })
                
                response = HttpResponse(content_type='application/pdf')
                response['Content-Disposition'] = f'filename="Dechargement-{seller.name}-{selected_date}.pdf"'
                pisa.CreatePDF(html, dest=response)
                return response
            
            messages.success(request, "Déchargement d'inventaire enregistré avec succès.")
            return redirect('sellers:unload_inventory')
    else:
        form = UnloadInventoryForm(initial={'date': now().date()})
    
    return render(request, 'sellers/unload_inventory.html', {
        'form': form,
    })
