from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.forms import inlineformset_factory
from django.urls import reverse
from .models import Purchase, PurchaseItem, SupplierPayment
from .forms import PurchaseForm, PurchaseItemFormSet, SupplierPaymentForm
from django.db import models
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET
from products.models import Product, Category

from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET
from products.models import Product
import json
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Purchase, PurchaseItem
from .forms import PurchaseForm
from products.models import Product
from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from .models import Purchase
from configuration.models import CompanySettings
from django.utils import timezone
from .models import Purchase

from django.shortcuts import render
from django.db.models import Q, F
from .models import Purchase
from suppliers.models import Supplier
from datetime import datetime
from django.contrib.auth.decorators import login_required

from inventory.models import Stock, Warehouse, StockMovement
from django.db.models import F

def purchase_list_view(request):
    purchases = Purchase.objects.select_related('supplier').all()
    suppliers = Supplier.objects.all()

    # --- Filtres ---
    supplier_id = request.GET.get('supplier')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if supplier_id:
        purchases = purchases.filter(supplier_id=supplier_id)

    if start_date:
        try:
            purchases = purchases.filter(date__gte=datetime.strptime(start_date, "%Y-%m-%d"))
        except:
            pass

    if end_date:
        try:
            purchases = purchases.filter(date__lte=datetime.strptime(end_date, "%Y-%m-%d"))
        except:
            pass

    # --- Tri ---
    sort = request.GET.get('sort')
    if sort == 'montant':
        purchases = purchases.order_by('-total_amount')
    elif sort == 'statut':
        purchases = purchases.annotate(
            is_paid=F('amount_paid') >= F('total_amount')
        ).order_by('-is_paid')
    else:
        purchases = purchases.order_by('-date')

    return render(request, 'purchases/purchase_list.html', {
        'purchases': purchases,
        'suppliers': suppliers,
        'filters': {
            'supplier': supplier_id,
            'start_date': start_date,
            'end_date': end_date,
            'sort': sort,
        }
    })

# Détail d'un achat
def purchase_detail(request, pk):
    purchase = get_object_or_404(Purchase, pk=pk)
    items = purchase.items.select_related("product")
    payments = purchase.payments.all()
    return render(request, "purchases/purchase_detail.html", {
        "purchase": purchase,
        "items": items,
        "payments": payments,
    })

def purchase_create(request):
    if request.method == "POST":
        form = PurchaseForm(request.POST)
        products_json = request.POST.get("products_data")

        if form.is_valid():
            try:
                products_data = json.loads(products_json)
            except json.JSONDecodeError:
                messages.error(request, "Erreur de format des produits.")
                return render(request, "purchases/purchase_form.html", {"form": form})

            if not products_data:
                messages.error(request, "Veuillez ajouter au moins un produit.")
                return render(request, "purchases/purchase_form.html", {"form": form})

            purchase = form.save(commit=False)
            total = 0
            items = []

            for entry in products_data:
                try:
                    product = Product.objects.get(id=entry["product_id"])
                except Product.DoesNotExist:
                    messages.error(request, f"Produit introuvable (ID {entry['product_id']}).")
                    return render(request, "purchases/purchase_form.html", {"form": form})

                quantity = int(entry["quantity"])
                unit_price = float(entry["unit_price"])
                subtotal = quantity * unit_price
                total += subtotal

                item = PurchaseItem(
                    purchase=purchase,
                    product=product,
                    quantity=quantity,
                    unit_price=unit_price,
                    subtotal=subtotal
                )
                items.append(item)

            purchase.total_amount = total
            purchase.save()

            # Enregistrer les lignes
            for item in items:
                item.purchase = purchase
                item.save()

            messages.success(request, "Achat enregistré avec succès.")
            return redirect("purchases:purchase_detail", pk=purchase.pk)
        else:
            messages.error(request, "Formulaire invalide.")
    else:
        form = PurchaseForm()

    return render(request, "purchases/purchase_form.html", {
        "form": form
    })

# Ajouter un paiement fournisseur
@login_required
def add_supplier_payment(request, purchase_id):
    purchase = get_object_or_404(Purchase, id=purchase_id)
    
    if request.method == 'POST':
        form = SupplierPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.purchase = purchase
            payment.save()
            
            # Update the purchase's amount_paid
            purchase.update_amount_paid()
            
            messages.success(request, "Paiement enregistré avec succès.")
            return redirect('purchases:purchase_detail', pk=purchase.id)
    else:
        form = SupplierPaymentForm()
    
    return render(request, 'purchases/add_payment.html', {
        'purchase': purchase,
        'form': form
    })

@require_GET
def product_selector(request):
    search = request.GET.get("search", "").strip()
    category_id = request.GET.get("category")

    print("🔍 Requête AJAX reçue")  # ← debug
    print("Recherche :", search)
    print("Catégorie ID :", category_id)

    products = Product.objects.all()

    if search:
        products = products.filter(name__icontains=search)
    if category_id:
        products = products.filter(category_id=category_id)

    print(f"Produits trouvés : {products.count()}")  # ← debug

    html = render_to_string("purchases/partials/product_selector_list.html", {
        "products": products,
    })

    return JsonResponse({"html": html})

def purchase_order_pdf(request, pk):
    purchase = Purchase.objects.get(pk=pk)
    company = CompanySettings.objects.first()
    template = get_template("purchases/purchase_order_pdf.html")
    html = template.render({"purchase": purchase, "company": company,})

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="bon-commande-{purchase.id}.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse("Erreur lors de la génération du PDF", status=500)

    return response

def purchases_due_list(request):
    today = timezone.now().date()
    purchases = Purchase.objects.filter(status='confirmed', total_amount__gt=0)
    purchases = purchases.annotate(
        paid=models.Sum('payments__amount')
    ).filter(total_amount__gt=models.F('paid'))

    return render(request, "purchases/purchases_due_list.html", {
        "purchases": purchases,
        "today": today,
    })

def receive_purchase(request, pk):
    purchase = get_object_or_404(Purchase, pk=pk)
    if request.method == "POST":
        warehouse = Warehouse.objects.first()
        if not warehouse:
            messages.error(request, "Aucun entrepôt trouvé.")
            return redirect("purchases:purchase_detail", pk=purchase.pk)

        for item in purchase.items.all():
            # Create stock movement - the signal will handle the stock update
            StockMovement.objects.create(
                product=item.product,
                warehouse=warehouse,
                movement_type='in',
                quantity=item.quantity,
                source=f"Réception commande #{purchase.id}",
                user=request.user
            )

        purchase.status = "received"
        purchase.save()
        messages.success(request, "Commande reçue et stock mis à jour.")
        return redirect("purchases:purchase_detail", pk=purchase.pk)

    return render(request, "purchases/receive_confirmation.html", {"purchase": purchase})
