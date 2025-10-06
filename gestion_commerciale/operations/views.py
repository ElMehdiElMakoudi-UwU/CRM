# operations/views.py
from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import get_template
from django.utils.timezone import now
from django.urls import reverse
from django.contrib import messages
from django.db.models import F

# Third-party library for PDF generation (Requires: pip install xhtml2pdf)
import xhtml2pdf.pisa as pisa

# Import models from the local app
from .models import Seller, SellerProductDayEntry
# Import Product from the separate 'products' app
from products.models import Product 
# Import the Stock and StockMovement models from the 'inventory' app
from inventory.models import Stock, StockMovement 

# --- Inventory Loading View ---
@login_required
def load_new_inventory(request):
    """
    Handles the loading (chargement) of inventory onto a seller's vehicle.
    Calculates previous day's returns as today's starting 'voiture' stock.
    Saves loading data and generates a PDF report.
    """
    sellers = Seller.objects.all()
    products = Product.objects.all()
    voiture_quantities = {} # Stores carried-over stock (voiture)

    selected_seller = None
    selected_seller_id = request.GET.get('seller') or request.POST.get('seller')
    selected_date_str = request.GET.get('date') or request.POST.get('date')
    selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date() if selected_date_str else now().date()

    if selected_seller_id:
        try:
            selected_seller = get_object_or_404(Seller, id=selected_seller_id)
        except Seller.DoesNotExist:
            messages.error(request, "Vendeur non trouvé.")
            selected_seller_id = None 

    if selected_seller:
        # 1. Calculate 'voiture' (carry-over stock) from yesterday's returns
        yesterday = selected_date - timedelta(days=1)
        
        # Fetch all previous entries in one query
        yesterday_entries = SellerProductDayEntry.objects.filter(
            seller=selected_seller, 
            date=yesterday
        ).select_related('product')
        
        # Map yesterday's 'retour' (return) to today's 'voiture'
        for entry in yesterday_entries:
            voiture_quantities[entry.product_id] = entry.retour

        if request.method == 'POST':
            entries = []
            
            for product in products:
                try:
                    sortie_qty = int(request.POST.get(f'sortie_{product.id}', 0)) 
                except ValueError:
                    sortie_qty = 0
                    
                voiture_qty = voiture_quantities.get(product.id, 0)

                if sortie_qty > 0 or voiture_qty > 0:
                    
                    entry, created = SellerProductDayEntry.objects.update_or_create(
                        seller=selected_seller,
                        product=product,
                        date=selected_date,
                        defaults={
                            'voiture': voiture_qty,
                            'sortie': sortie_qty,
                            'retour': 0, # Reset return to 0 during loading
                        }
                    )
                    
                    entry.total_loaded = entry.voiture + entry.sortie
                    entry.save()
                    entries.append(entry)
            
            filtered_entries = [entry for entry in entries if entry.total_loaded > 0]

            # Generate PDF Report
            template = get_template('pdf/load_report.html')
            html = template.render({
                'seller': selected_seller,
                'date': selected_date,
                'entries': filtered_entries,
            })

            response = HttpResponse(content_type='application/pdf')
            filename = f"Chargement-{selected_seller.name.replace(' ', '_')}-{selected_date}.pdf"
            response['Content-Disposition'] = f'filename="{filename}"'
            
            pisa_status = pisa.CreatePDF(html, dest=response)
            
            if pisa_status.err:
                messages.error(request, "Erreur lors de la génération du PDF de chargement.")
                return redirect(reverse('operations:load_new_inventory')) 
            
            messages.success(request, f"Chargement enregistré pour {selected_seller.name}.")
            return response

    # Handle GET request or initial view display
    return render(request, 'operations/load_new_inventory.html', {
        'sellers': sellers,
        'products': products,
        'voiture_quantities': voiture_quantities,
        'selected_seller_id': selected_seller_id,
        'selected_date': selected_date.strftime('%Y-%m-%d'),
        'selected_seller': selected_seller,
    })

# --- Inventory Unloading View ---
@login_required
def unload_new_inventory(request):
    """
    Handles the unloading (déchargement) of inventory, calculates sales, 
    and updates the global Product stock via the Stock model, logging a 
    StockMovement for the audit trail.
    """
    seller_id = request.GET.get("seller")
    date_str = request.GET.get("date")
    
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else now().date()

    seller = None
    entry_data = [] 

    if seller_id:
        try:
            seller = get_object_or_404(Seller, id=seller_id)
        except Seller.DoesNotExist:
            messages.error(request, "Vendeur non trouvé.")
            seller_id = None

    if seller:
        # Fetch today's entry data (voiture, sortie, and previous retour if any)
        today_entries = SellerProductDayEntry.objects.filter(
            seller=seller, 
            date=selected_date
        ).select_related('product')
        
        # Prepare data for display and POST processing
        for entry in today_entries:
            entry.total_loaded = entry.voiture + entry.sortie
            if entry.total_loaded > 0:
                entry_data.append(entry)

        if request.method == "POST":
            if not entry_data:
                messages.error(request, "Aucun chargement trouvé pour cette date. Impossible de décharger.")
                return redirect(reverse('operations:unload_new_inventory') + f'?seller={seller_id}&date={selected_date.strftime("%Y-%m-%d")}')

            for entry in entry_data:
                product = entry.product
                
                try:
                    retour_qty = int(request.POST.get(f"retour_{product.id}", 0))
                except ValueError:
                    retour_qty = 0
                
                total_loaded = entry.voiture + entry.sortie
                
                # Input validation: returns cannot exceed total loaded
                if retour_qty > total_loaded:
                    messages.warning(request, f"Avertissement: Le retour de {product.name} ({retour_qty}) a été plafonné au stock chargé ({total_loaded}).")
                    retour_qty = total_loaded

                # Calculate "before" sold quantity for stock difference check
                previous_vendu = entry.vendu 

                # Update the entry fields
                entry.retour = retour_qty
                entry.vendu = total_loaded - entry.retour
                entry.amount = entry.vendu * product.selling_price
                
                entry.save() 
                
                # Calculate the difference in sales (The net change in stock consumption)
                sold_difference = entry.vendu - previous_vendu
                
                # --- STOCK DEDUCTION LOGIC WITH MOVEMENT LOGGING ---
                if sold_difference != 0:
                    if product.default_warehouse:
                        warehouse = product.default_warehouse
                        
                        if sold_difference > 0:
                            # 1. Update Stock quantity (Deduct sales)
                            Stock.objects.filter(
                                product=product,
                                warehouse=warehouse
                            ).update(
                                quantity=F('quantity') - sold_difference
                            )

                            # 2. Log Stock Movement (Sale/Out)
                            StockMovement.objects.create(
                                product=product,
                                warehouse=warehouse,
                                movement_type='out',
                                quantity=sold_difference,
                                source=f'vente_vendeur: {seller.name}',
                                user=request.user
                            )
                        
                        elif sold_difference < 0:
                            # If sold_difference is negative, stock needs to be restored (e.g., corrected return)
                            restored_quantity = abs(sold_difference)
                            
                            # 1. Update Stock quantity (Restore stock)
                            Stock.objects.filter(
                                product=product,
                                warehouse=warehouse
                            ).update(
                                quantity=F('quantity') + restored_quantity
                            )

                            # 2. Log Stock Movement (Adjustment/Correction)
                            StockMovement.objects.create(
                                product=product,
                                warehouse=warehouse,
                                movement_type='adjustment', 
                                quantity=restored_quantity,
                                source=f'correction_dechargement: {seller.name}',
                                user=request.user
                            )
                    else:
                        messages.warning(request, f"Impossible de mettre à jour le stock global pour {product.name}: Aucun entrepôt par défaut trouvé.")
                    
            messages.success(request, f"Déchargement enregistré pour {seller.name} et stock global mis à jour.")

            # Redirect to the PDF export view
            pdf_url = reverse('operations:export_unload_pdf', args=[seller.id, selected_date])
            return redirect(pdf_url)

    # Handle GET request
    return render(request, "operations/unload_new_inventory.html", {
        "sellers": Seller.objects.all(),
        "selected_seller": seller,
        "selected_date": selected_date.strftime('%Y-%m-%d'),
        "entry_data": entry_data, 
        "seller_id": seller_id,
    })


# --- PDF Export View for Unloading ---
@login_required
def export_unload_pdf(request, seller_id, date_str):
    """
    Generates a PDF report for the day's unloading operation (sales summary).
    """
    seller = get_object_or_404(Seller, id=seller_id)
    selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()

    entries = SellerProductDayEntry.objects.filter(
        seller=seller, 
        date=selected_date,
        vendu__gt=0 
    ).select_related('product')
    
    total_amount = sum(entry.amount for entry in entries)

    template = get_template('pdf/unload_report.html')
    html = template.render({
        'seller': seller,
        'date': selected_date,
        'entries': entries,
        'total_amount': total_amount,
    })

    response = HttpResponse(content_type='application/pdf')
    filename = f"Dechargement-Ventes-{seller.name.replace(' ', '_')}-{selected_date}.pdf"
    response['Content-Disposition'] = f'filename="{filename}"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        messages.error(request, "Erreur lors de la génération du PDF de déchargement.")
        return redirect(reverse('operations:unload_new_inventory')) 

    return response