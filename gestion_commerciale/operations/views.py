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
from django.db import transaction
from decimal import Decimal

# Third-party library for PDF generation (Requires: pip install xhtml2pdf)
import xhtml2pdf.pisa as pisa

# Import models from the local app
from .models import Seller, SellerProductDayEntry
# Import Product from the separate 'products' app
from products.models import Product 
# Import the Stock and StockMovement models from the 'inventory' app
from inventory.models import Stock, StockMovement 


# --- Inventory Loading View (Chargement) ---
@login_required
def load_new_inventory(request):
    """
    Handles the loading (chargement) of inventory onto a seller's vehicle.
    Calculates carry-over stock ('voiture') based on the last recorded date 
    and debits central stock upon load.
    """
    sellers = Seller.objects.all()
    products = Product.objects.all()
    voiture_quantities = {} 

    selected_seller = None
    selected_seller_id = request.GET.get('seller') or request.POST.get('seller')
    
    # Get the selected date or default to today
    selected_date_str = request.GET.get('date') or request.POST.get('date')
    selected_date = now().date()
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Format de date invalide.")

    if selected_seller_id:
        selected_seller = get_object_or_404(Seller, id=selected_seller_id)

    if selected_seller:
        # --- PRE-LOAD: VOITURE CALCULATION ---
        # Calculate "Voiture" (Carry-Over Stock) from the last entry's retour
        # Logic: The last entry's returned stock (retour) becomes today's carry-over stock (voiture)
        # This handles gaps in work days (e.g., weekends) by finding the most recent entry
        for product in products: 
            # Look up the last entry for this seller and product before the selected date
            last_entry = SellerProductDayEntry.objects.filter(
                seller=selected_seller, 
                product=product, 
                date__lt=selected_date
            ).order_by('-date').first()
            
            # The last entry's retour becomes today's voiture
            voiture_quantities[product.id] = last_entry.retour if last_entry else Decimal('0.00')

        # --- Handle POST Request (Saving the Load) ---
        if request.method == 'POST':
            entries = []
            
            try:
                with transaction.atomic():
                    for product in products:
                        try:
                            sortie_qty = Decimal(request.POST.get(f'sortie_{product.id}', 0)) 
                        except ValueError:
                            sortie_qty = Decimal('0.00')
                            
                        voiture_qty = voiture_quantities.get(product.id, Decimal('0.00'))
                        
                        # Calculate total_loaded = voiture + sortie
                        total_loaded = voiture_qty + sortie_qty
                        
                        if sortie_qty > 0 or voiture_qty > 0:
                            
                            # Create or update the day entry
                            entry, created = SellerProductDayEntry.objects.update_or_create(
                                seller=selected_seller,
                                product=product,
                                date=selected_date,
                                defaults={
                                    'voiture': voiture_qty,
                                    'sortie': sortie_qty,
                                    'total_loaded': total_loaded,  # Calculate and save total_loaded
                                    'retour': Decimal('0.00'),  # Initialize retour to 0 at this stage
                                }
                            )
                            entries.append(entry)

                            # --- DEBIT CENTRAL STOCK ---
                            if sortie_qty > 0:
                                if hasattr(product, 'default_warehouse') and product.default_warehouse:
                                    warehouse = product.default_warehouse
                                    
                                    # 1. Update Stock quantity (Deduct load)
                                    Stock.objects.filter(
                                        product=product,
                                        warehouse=warehouse
                                    ).update(
                                        quantity=F('quantity') - sortie_qty
                                    )

                                    # 2. Log Stock Movement (Load/Out)
                                    StockMovement.objects.create(
                                        product=product,
                                        warehouse=warehouse,
                                        movement_type='load', 
                                        quantity=sortie_qty,
                                        source=f'chargement_vendeur: {selected_seller.name}',
                                        user=request.user
                                    )
                                else:
                                    print(f"WARNING: Cannot debit stock for {product.name}: No default warehouse.")


                messages.success(request, f"Chargement enregistré pour {selected_seller.name}.")
                
                # Generate PDF Report
                # Filter entries where total_loaded > 0
                filtered_entries = [e for e in entries if e.total_loaded > 0]
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
                
                return response

            except Exception as e:
                messages.error(request, f"Erreur lors de l'enregistrement du chargement: {e}")
                
    # Handle GET request or initial view display
    return render(request, 'operations/load_new_inventory.html', {
        'sellers': sellers,
        'products': products,
        'voiture_quantities': voiture_quantities,
        'selected_seller_id': selected_seller_id,
        'selected_date': selected_date.strftime('%Y-%m-%d'),
        'selected_seller': selected_seller,
    })    


# 📦 Inventory Unloading View (Déchargement)

@login_required
def unload_new_inventory(request):
    """
    Handles the unloading (déchargement) of inventory, calculating sales, and updating 
    global stock. Dynamically determines the most recent date needing reconciliation 
    based on outstanding loaded quantities.
    """
    seller_id = request.GET.get("seller")
    reconciliation_date_str = request.GET.get("date")
    
    seller = None
    entry_data = [] 
    reconciliation_date = now().date()

    if seller_id:
        seller = get_object_or_404(Seller, id=seller_id)

    if seller:
        # --- 1. DETERMINE RECONCILIATION DATE ---
        if not reconciliation_date_str:
            # Find the date of the MOST RECENT entry the seller was active on.
            latest_load_date = SellerProductDayEntry.objects.filter(
                seller=seller,
                date__lte=now().date()
            ).order_by('-date').values_list('date', flat=True).first()
            
            if latest_load_date:
                reconciliation_date = latest_load_date
            else:
                messages.error(request, f"Aucun historique de chargement trouvé pour {seller.name}. Impossible de décharger.")
                reconciliation_date_str = reconciliation_date.strftime('%Y-%m-%d') # Fallback date string
                
                return render(request, "operations/unload_new_inventory.html", {
                    "sellers": Seller.objects.all(),
                    "selected_seller": seller,
                    "selected_date": reconciliation_date_str,
                    "entry_data": [], 
                    "seller_id": seller_id,
                })
        else:
            try:
                reconciliation_date = datetime.strptime(reconciliation_date_str, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, "Format de date invalide.")
                
        reconciliation_date_str = reconciliation_date.strftime('%Y-%m-%d')
        
        # --- 2. FETCH ENTRIES FOR RECONCILIATION ---
        today_entries = SellerProductDayEntry.objects.filter(
            seller=seller, 
            date=reconciliation_date
        ).select_related('product')
        
        # 3. Prepare entry data for display
        # The entry already contains "Voiture" (starting stock) and "Sortie" (loaded stock) from the load phase
        for entry in today_entries:
            # Ensure total_loaded is calculated (should already be saved from load phase)
            if not entry.total_loaded:
                entry.total_loaded = entry.voiture + entry.sortie
                entry.save(update_fields=['total_loaded'])
            
            # Check if there is remaining stock to be reconciled (loaded > returned)
            entry.remaining_stock = entry.total_loaded - entry.retour
            
            # Only display items that still need reconciliation
            if entry.remaining_stock > Decimal('0.00'):
                 entry_data.append(entry)
        
        if not entry_data and request.method == "GET":
            messages.info(request, f"Le chargement du **{reconciliation_date_str}** semble déjà entièrement déchargé. Veuillez choisir une autre date si nécessaire.")
            
        # --- Handle POST Request (Reconciliation) ---
        if request.method == "POST":
            # Re-fetch entries to ensure we use the current database state
            entries_to_process = SellerProductDayEntry.objects.filter(
                seller=seller, date=reconciliation_date
            ).select_related('product')

            try:
                with transaction.atomic():
                    for entry in entries_to_process:
                        product = entry.product
                        
                        try:
                            # Use Decimal for input consistency
                            retour_qty = Decimal(request.POST.get(f"retour_{product.id}", 0))
                        except ValueError:
                            retour_qty = Decimal('0.00')
                        
                        # Get total_loaded (should already be calculated from load phase)
                        total_loaded = entry.total_loaded if entry.total_loaded else (entry.voiture + entry.sortie)
                        previous_retour = entry.retour
                        
                        # Input validation: returns cannot exceed total loaded
                        if retour_qty > total_loaded:
                            messages.warning(request, f"Avertissement: Le retour de {product.name} ({retour_qty}) a été plafonné au stock chargé ({total_loaded}).")
                            retour_qty = total_loaded

                        # Calculate "before" sold quantity (Vendu before this submission)
                        previous_vendu = total_loaded - previous_retour 

                        # Recalculate Vendu (Sales) using the core reconciliation formula:
                        # Vendu = (Voiture + Sortie) - Retour
                        vendu = total_loaded - retour_qty
                        
                        # Calculate Amount: Vendu * Product Selling Price
                        amount = vendu * product.selling_price

                        # Update the entry fields
                        entry.retour = retour_qty
                        entry.vendu = vendu
                        entry.amount = amount
                        
                        entry.save() 
                        
                        # Calculate the net change in stock consumption (sold_difference)
                        sold_difference = entry.vendu - previous_vendu
                        
                        # --- UPDATE GLOBAL WAREHOUSE STOCK ---
                        # Calculate the sold_difference (the amount sold after any previous reconciliation)
                        # Update the central warehouse stock by deducting the sold_difference atomically
                        if sold_difference != 0:
                            if hasattr(product, 'default_warehouse') and product.default_warehouse:
                                warehouse = product.default_warehouse
                                
                                if sold_difference > 0:
                                    # Sales increased -> Deduct more from Stock
                                    # Update Product.quantity (via Stock model) by deducting sold_difference
                                    Stock.objects.filter(
                                        product=product,
                                        warehouse=warehouse
                                    ).update(
                                        quantity=F('quantity') - sold_difference
                                    )

                                    StockMovement.objects.create(
                                        product=product,
                                        warehouse=warehouse,
                                        movement_type='sale_out',
                                        quantity=sold_difference,
                                        source=f'vente_vendeur: {seller.name}',
                                        user=request.user
                                    )
                                
                                elif sold_difference < 0:
                                    # Sales decreased (more returned) -> Restore stock
                                    restored_quantity = abs(sold_difference)
                                    
                                    Stock.objects.filter(
                                        product=product,
                                        warehouse=warehouse
                                    ).update(
                                        quantity=F('quantity') + restored_quantity
                                    )

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
                        
                messages.success(request, f"Déchargement enregistré pour {seller.name} (Date: {reconciliation_date_str}) et stock global mis à jour.")

                # Redirect to the PDF export view
                pdf_url = reverse('operations:export_unload_pdf', args=[seller.id, reconciliation_date_str])
                return redirect(pdf_url)

            except Exception as e:
                messages.error(request, f"Erreur lors de la décharge: {e}")
                
    # Handle GET request
    return render(request, "operations/unload_new_inventory.html", {
        "sellers": Seller.objects.all(),
        "selected_seller": seller,
        "selected_date": reconciliation_date_str,
        "entry_data": entry_data, 
        "seller_id": seller_id,
    })



# 📄 PDF Export View for Unloading

@login_required
def export_unload_pdf(request, seller_id, date_str):
    """
    Generates a PDF report for the day's unloading operation (sales summary).
    """
    seller = get_object_or_404(Seller, id=seller_id)
    
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, "Date de rapport invalide.")
        return redirect(reverse('operations:unload_new_inventory')) 

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