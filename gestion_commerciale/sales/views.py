from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Q
from django.http import HttpResponse, FileResponse, JsonResponse
from django.template.loader import get_template, render_to_string
from django.utils import timezone

from datetime import datetime, date
from calendar import monthrange
from decimal import Decimal
import io

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from xhtml2pdf import pisa

from .models import Sale, SaleItem, Payment
from .forms import SaleForm, SaleItemFormSet, PaymentForm
from products.models import Product, Category
from inventory.models import StockMovement
from clients.models import Client
from .services import UnifiedSalesService
from pricing.services import PricingService
from inventory.models import Warehouse

def sale_list(request):
    sales = Sale.objects.select_related('client').order_by('-date')

    query = request.GET.get('q')
    date_filter = request.GET.get('date_filter')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if query:
        sales = sales.filter(client__name__icontains=query)

    if date_filter == 'today':
        today = datetime.today().date()
        sales = sales.filter(date__date=today)
    elif date_filter == 'month':
        today = datetime.today().date()
        sales = sales.filter(date__month=today.month, date__year=today.year)
    elif start_date and end_date:
        sales = sales.filter(date__date__range=[start_date, end_date])

    return render(request, 'sales/sale_list.html', {
        'sales': sales,
        'filters': {
            'q': query or '',
            'date_filter': date_filter or '',
            'start_date': start_date or '',
            'end_date': end_date or '',
        }
    })


def sale_detail(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    items = sale.items.all()
    payments = sale.payments.all()
    return render(request, 'sales/sale_detail.html', {
        'sale': sale,
        'items': items,
        'payments': payments
    })

from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from .models import Sale
from django.shortcuts import get_object_or_404

def sale_invoice_pdf(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    template = get_template("sales/invoice_pdf.html")

    html = template.render({
        "sale": sale,
        "company": request.user.company if hasattr(request.user, 'company') else None
    })

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'filename="facture_{sale.id}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("Erreur lors de la génération du PDF", status=500)
    return response

from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from products.models import Product, Category
from .models import Sale, SaleItem, Payment
from inventory.models import StockMovement
from clients.models import Client
from .forms import SaleForm, PaymentForm
from django.utils import timezone

@login_required
def get_product_price(request):
    """
    Vue Ajax pour obtenir le prix d'un produit pour un client spécifique
    """
    if request.method == "GET":
        product_id = request.GET.get('product_id')
        client_id = request.GET.get('client_id')
        quantity = int(request.GET.get('quantity', 1))

        try:
            product = Product.objects.get(id=product_id)
            client = Client.objects.get(id=client_id)
            
            price = PricingService.get_price_for_client(client, product, quantity)
            
            return JsonResponse({
                'success': True,
                'price': str(price),
                'product_name': product.name
            })
        except (Product.DoesNotExist, Client.DoesNotExist):
            return JsonResponse({
                'success': False,
                'error': 'Produit ou client non trouvé'
            })
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

@login_required
@transaction.atomic
def sale_create(request):
    if request.method == "POST":
        form = SaleForm(request.POST)
        payment_form = PaymentForm(request.POST)

        product_ids = request.POST.getlist('products[]')
        quantities = request.POST.getlist('quantities[]')
        unit_prices = request.POST.getlist('unit_prices[]')

        if form.is_valid() and payment_form.is_valid() and product_ids:
            client = form.cleaned_data['client']
            notes = form.cleaned_data['notes']
            amount_paid = payment_form.cleaned_data['amount']
            warehouse = Warehouse.objects.filter(is_active=True).first()

            sale = Sale.objects.create(
                client=client,
                warehouse=warehouse,
                user=request.user,
                date=timezone.now(),
                total_amount=0,  # temp, will override later
                amount_paid=amount_paid,
                notes=notes,
            )

            total_sale = 0
            for i, product_id in enumerate(product_ids):
                product = Product.objects.get(id=product_id)
                quantity = Decimal(quantities[i])
                
                # Utiliser le service de tarification pour obtenir le prix unitaire HT
                unit_price_ht = PricingService.get_price_for_client(client, product, int(quantity))
                # Calculer le prix TTC
                unit_price_ttc = unit_price_ht * (1 + product.tax_rate / 100)
                total = quantity * unit_price_ttc
                total_sale += total

                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    quantity=quantity,
                    unit_price=unit_price_ttc  # Stocker le prix TTC
                )

                # Update stock (sortie)
                StockMovement.objects.create(
                    product=product,
                    warehouse=warehouse,
                    movement_type='out',
                    quantity=quantity,
                    source=f"Vente #{sale.id}",
                    user=request.user
                )

            # Update sale total
            sale.total_amount = total_sale
            sale.save()

            # Save payment
            Payment.objects.create(
                sale=sale,
                amount=amount_paid,
                date=sale.date,
                method=payment_form.cleaned_data['method'],
            )

            # Update client balance if partial payment
            if amount_paid < sale.total_amount_ttc:
                client.balance += Decimal(str(sale.total_amount_ttc)) - amount_paid
                client.save()

            messages.success(request, 'Vente créée avec succès.')
            return redirect('sales:sale_detail', pk=sale.id)
        else:
            messages.error(request, 'Erreur lors de la création de la vente.')
    else:
        form = SaleForm()
        payment_form = PaymentForm()

    categories = Category.objects.all()
    products = Product.objects.filter(is_active=True)
    
    return render(request, 'sales/sale_form.html', {
        'form': form,
        'payment_form': payment_form,
        'categories': categories,
        'products': products,
    })

def monthly_sales(request):
    # Obtenir le mois et l'année depuis les paramètres ou utiliser le mois courant
    current_date = timezone.now().date()
    year = int(request.GET.get('year', current_date.year))
    month = int(request.GET.get('month', current_date.month))
    
    # Utiliser le service unifié pour obtenir toutes les ventes
    sales_data = UnifiedSalesService.get_monthly_sales(year, month)
    
    # Générer la liste des mois pour le filtre
    months = []
    for m in range(1, 13):
        months.append({
            'number': m,
            'name': date(2000, m, 1).strftime('%B')
        })
    
    # Générer la liste des années (de l'année -2 à l'année +1)
    current_year = timezone.now().year
    years = range(current_year - 2, current_year + 2)
    
    context = {
        'sales': sales_data['sales'],
        'totals': sales_data['totals'],
        'current_month': month,
        'current_year': year,
        'months': months,
        'years': years,
    }
    
    return render(request, 'sales/monthly_sales.html', context)

def generate_monthly_invoices_pdf(request):
    # Obtenir le mois et l'année depuis les paramètres
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))
    
    # Obtenir les informations de l'entreprise si disponibles
    company = request.user.company if hasattr(request.user, 'company') else None
    
    # Générer le PDF avec le service unifié
    buffer = UnifiedSalesService.generate_monthly_invoices_pdf(year, month, company)
    
    # Retourner le PDF
    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f'factures_{year}_{month}.pdf'
    )

@login_required
def search_products(request):
    """
    Vue Ajax pour rechercher des produits
    """
    query = request.GET.get('q', '')
    category_id = request.GET.get('category')

    products = Product.objects.all()

    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(reference__icontains=query)
        )

    if category_id:
        products = products.filter(category_id=category_id)

    products = products.select_related('category', 'default_warehouse')[:50]

    product_list = [{
        'id': p.id,
        'name': p.name,
        'reference': p.reference,
        'selling_price': str(p.selling_price),
        'price_with_tax': str(p.price_with_tax),
        'tax_rate': str(p.tax_rate),
        'category_name': p.category.name if p.category else '',
        'default_warehouse_id': p.default_warehouse.id if p.default_warehouse else None,
        'default_warehouse_name': p.default_warehouse.name if p.default_warehouse else None,
        'current_stock': p.total_stock,
    } for p in products]

    return JsonResponse({'products': product_list})



