from django.shortcuts import render, get_object_or_404, redirect
from django.forms import modelformset_factory
from django.contrib import messages
from django.db import transaction
from .models import Sale, SaleItem, Payment
from .forms import SaleForm, SaleItemFormSet, PaymentForm
from inventory.models import Stock, StockMovement
from clients.models import Client

from django.db.models import Q
from datetime import datetime

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
        "company": request.user.company if hasattr(request.user, 'company') else None  # optionnel
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
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from products.models import Product, Category
from .models import Sale, SaleItem, Payment
from inventory.models import StockMovement
from clients.models import Client
from .forms import SaleForm, PaymentForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from decimal import Decimal

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



