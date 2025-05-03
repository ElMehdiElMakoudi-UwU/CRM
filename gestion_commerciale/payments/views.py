# payments/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from clients.models import Client
from .forms import ClientPaymentForm, SalePaymentFormSet
from .models import ClientPayment, SalePayment
from django.db import models  # nécessaire pour models.Sum
from django.db.models import Sum
from django.db.models import F, ExpressionWrapper, DecimalField




# payments/views.py
from clients.models import Client, ClientSegment

@login_required
def client_debts_list(request):
    query = request.GET.get('search', '')
    segment_id = request.GET.get('segment', '')

    clients = Client.objects.filter(balance__gt=0)

    if query:
        clients = clients.filter(name__icontains=query)

    if segment_id:
        clients = clients.filter(segment_id=segment_id)

    total_debt = clients.aggregate(models.Sum('balance'))['balance__sum'] or 0
    count_debtors = clients.count()
    segments = ClientSegment.objects.all()

    return render(request, "payments/client_debts_list.html", {
        "clients": clients,
        "total_debt": total_debt,
        "count_debtors": count_debtors,
        "segments": segments,
        "selected_segment": segment_id,
        "search_query": query,
    })

# payments/views.py
from .forms import ClientPaymentForm, SalePaymentFormSet
from sales.models import Sale

# payments/views.py
from django.forms import formset_factory
from .forms import ClientPaymentForm, SaleAllocationForm

SaleAllocationFormSet = formset_factory(SaleAllocationForm, extra=0)

@login_required
def client_payment_create(request, client_id):
    client = get_object_or_404(Client, id=client_id)

    # 🔎 Sélection des ventes à crédit impayées
    unpaid_sales = Sale.objects.filter(
        client=client,
        is_credit=True
    ).annotate(
        balance_due=ExpressionWrapper(
            F('total_amount') - F('amount_paid'),
            output_field=DecimalField()
        )
    ).filter(balance_due__gt=0)

    if request.method == "POST":
        form = ClientPaymentForm(request.POST)
        formset = SaleAllocationFormSet(request.POST, form_kwargs={'client': client})
        if form.is_valid() and formset.is_valid():
            payment = form.save(commit=False)
            payment.client = client
            payment.user = request.user
            payment.save()

            total_linked = 0

            for f in formset:
                sale = f.cleaned_data.get('sale')
                amount = f.cleaned_data.get('amount')

                if sale and amount:
                    SalePayment.objects.create(sale=sale, payment=payment, amount=amount)

                    # Mise à jour du solde payé sur la vente
                    sale.amount_paid += amount
                    sale.save()

                    total_linked += amount

            client.balance -= total_linked
            client.save()

            return redirect("payments:client_debts_list")

        else:
            messages.error(request, "❌ Le formulaire contient des erreurs. Veuillez vérifier.")
    else:
        initial_data = [{'sale': s.id, 'amount': s.balance_due} for s in unpaid_sales]

        form = ClientPaymentForm()
        formset = SaleAllocationFormSet(initial=initial_data, form_kwargs={'client': client})

    return render(request, "payments/client_payment_form.html", {
        "client": client,
        "form": form,
        "formset": formset,
    })

# payments/views.py
@login_required
def client_payment_history(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    payments = ClientPayment.objects.filter(client=client).order_by('-date')
    total_paid = payments.filter(is_cancelled=False).aggregate(Sum('amount'))['amount__sum'] or 0

    return render(request, "payments/client_payment_history.html", {
        "client": client,
        "payments": payments,
        "total_paid": total_paid,
    })

# payments/views.py
@login_required
def cancel_payment(request, payment_id):
    payment = get_object_or_404(ClientPayment, id=payment_id, is_cancelled=False)
    client = payment.client

    if request.method == "POST":
        # Rétablir le solde
        client.balance += payment.amount
        client.save()

        # Marquer comme annulé
        payment.is_cancelled = True
        payment.save()

        messages.success(request, "Le paiement a été annulé avec succès.")
        return redirect("payments:client_payment_history", client.id)

    return render(request, "payments/confirm_cancel_payment.html", {"payment": payment})


# payments/views.py
import openpyxl
from django.http import HttpResponse

@login_required
def export_clients_debts_excel(request):
    query = request.GET.get('search', '')
    segment_id = request.GET.get('segment', '')

    clients = Client.objects.filter(balance__gt=0)

    if query:
        clients = clients.filter(name__icontains=query)

    if segment_id:
        clients = clients.filter(segment_id=segment_id)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Clients Débiteurs"
    ws.append(["Nom", "Téléphone", "Segment", "Solde (DH)"])

    for c in clients:
        ws.append([c.name, c.phone, c.segment.name if c.segment else "", float(c.balance)])

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response['Content-Disposition'] = 'attachment; filename=clients_debiteurs.xlsx'
    wb.save(response)
    return response

@login_required
def export_client_payments_excel(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    payments = ClientPayment.objects.filter(client=client).order_by('-date')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Paiements"
    ws.append(["Date", "Montant", "Méthode", "Utilisateur"])

    for p in payments:
        ws.append([p.date.strftime("%d/%m/%Y %H:%M"), float(p.amount), p.get_method_display(), str(p.user)])

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response['Content-Disposition'] = f'attachment; filename=paiements_{client.name}.xlsx'
    wb.save(response)
    return response

from xhtml2pdf import pisa
from django.template.loader import get_template

@login_required
def export_clients_debts_pdf(request):
    query = request.GET.get('search', '')
    segment_id = request.GET.get('segment', '')

    clients = Client.objects.filter(balance__gt=0)
    if query:
        clients = clients.filter(name__icontains=query)
    if segment_id:
        clients = clients.filter(segment_id=segment_id)

    template = get_template("payments/pdf/clients_debts_pdf.html")
    html = template.render({'clients': clients})
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="clients_debiteurs.pdf"'
    pisa.CreatePDF(html, dest=response)
    return response

@login_required
def export_client_payments_pdf(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    payments = ClientPayment.objects.filter(client=client).order_by('-date')

    template = get_template("payments/pdf/client_payments_pdf.html")
    html = template.render({'client': client, 'payments': payments})

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="paiements_{client.name}.pdf"'
    pisa.CreatePDF(html, dest=response)
    return response
