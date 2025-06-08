from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Q
from django.http import HttpResponse, FileResponse
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
@transaction.atomic
def sale_create(request):
    if request.method == "POST":
        form = SaleForm(request.POST)
        payment_form = PaymentForm(request.POST)

        product_ids = request.POST.getlist('products[]')
        quantities = request.POST.getlist('quantities[]')
        unit_prices = request.POST.getlist('unit_prices[]')

        print("🔎 POST received")
        print("Product IDs:", product_ids)
        print("Quantities:", quantities)
        print("Unit prices:", unit_prices)
        print("Form valid?", form.is_valid())
        print("Form errors:", form.errors)
        print("Payment form valid?", payment_form.is_valid())
        print("Payment form errors:", payment_form.errors)

        if form.is_valid() and payment_form.is_valid() and product_ids:
            client = form.cleaned_data['client']
            notes = form.cleaned_data['notes']
            amount_paid = payment_form.cleaned_data['amount']

            sale = Sale.objects.create(
                client=client,
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
                unit_price = Decimal(unit_prices[i])
                total = quantity * unit_price
                total_sale += total

                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    quantity=quantity,
                    unit_price=unit_price
                )

                # Update stock (sortie)
                StockMovement.objects.create(
                    product=product,
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
            if amount_paid < total_sale:
                client.balance += total_sale - amount_paid
                client.save()

            print("✅ Vente enregistrée avec succès")
            messages.success(request, "Vente enregistrée avec succès.")
            return redirect('sales:sale_list')
        else:
            print("❌ Formulaire invalide ou aucun produit sélectionné.")
            messages.error(request, "Formulaire invalide ou aucun produit sélectionné.")
    else:
        form = SaleForm()
        payment_form = PaymentForm()

    context = {
        'form': form,
        'payment_form': payment_form,
        'categories': Category.objects.all(),
    }
    return render(request, 'sales/sale_form.html', context)

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



