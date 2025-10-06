from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from datetime import timedelta
from django.utils import timezone

# Import des modèles
from sales.models import Sale
from pos.models import POSReceipt
from products.models import Product
from inventory.models import Stock, StockAlert
from clients.models import Client
from purchases.models import Purchase


@login_required
def dashboard_home(request):
    total_sales = Sale.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    total_pos = POSReceipt.objects.aggregate(total=Sum('total'))['total'] or 0
    total_clients = Client.objects.count()
    total_stock_value = Stock.objects.aggregate(total=Sum('quantity'))['total'] or 0

    return render(request, 'dashboard/home.html', {
        'total_sales': total_sales,
        'total_pos': total_pos,
        'total_clients': total_clients,
        'total_stock_value': total_stock_value,
    })


@login_required
def sales_dashboard_view(request):
    sales_by_day = (
        Sale.objects.annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(total=Sum('total'))
        .order_by('day')
    )
    labels = [item['day'].strftime('%d/%m') for item in sales_by_day]
    values = [float(item['total']) for item in sales_by_day]

    top_products = (
        Product.objects.annotate(total_sales=Sum('movements__quantity'))
        .order_by('-total_sales')[:5]
    )

    return render(request, 'dashboard/sales.html', {
        'labels': labels,
        'values': values,
        'top_products': top_products,
    })


@login_required
def pos_dashboard_view(request):
    pos_by_day = (
        POSReceipt.objects.annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(total=Sum('total'))
        .order_by('day')
    )
    labels = [item['day'].strftime('%d/%m') for item in pos_by_day]
    values = [float(item['total']) for item in pos_by_day]

    caissiers = (
        POSReceipt.objects.values('cashier__username')
        .annotate(total=Sum('total'))
        .order_by('-total')[:5]
    )

    return render(request, 'dashboard/pos.html', {
        'labels': labels,
        'values': values,
        'caissiers': caissiers,
    })


@login_required
def stock_dashboard_view(request):
    total_value = Stock.objects.aggregate(total=Sum('quantity'))['total'] or 0
    alerts = StockAlert.objects.select_related('product', 'warehouse').filter(is_resolved=False)

    stock_by_warehouse = (
        Stock.objects.values('warehouse__name')
        .annotate(total=Sum('quantity'))
        .order_by('-total')
    )

    return render(request, 'dashboard/stock.html', {
        'total_value': total_value,
        'alerts': alerts,
        'stock_by_warehouse': stock_by_warehouse,
    })


@login_required
def clients_dashboard_view(request):
    now = timezone.now()
    active_clients = Client.objects.filter(sales__created_at__gte=now - timedelta(days=60)).distinct().count()
    inactive_clients = Client.objects.exclude(sales__created_at__gte=now - timedelta(days=60)).count()

    top_clients = (
        Client.objects.annotate(total=Sum('sales__total'))
        .order_by('-total')[:5]
    )

    return render(request, 'dashboard/clients.html', {
        'active_clients': active_clients,
        'inactive_clients': inactive_clients,
        'top_clients': top_clients,
    })


@login_required
def purchases_dashboard_view(request):
    purchases_by_supplier = (
        Purchase.objects.values('supplier__name')
        .annotate(total=Sum('total_amount'))
        .order_by('-total')[:5]
    )

    purchases_by_day = (
        Purchase.objects.annotate(day=TruncDate('date'))
        .values('day')
        .annotate(total=Sum('total_amount'))
        .order_by('day')
    )

    labels = [item['day'].strftime('%d/%m') for item in purchases_by_day]
    values = [float(item['total']) for item in purchases_by_day]

    return render(request, 'dashboard/purchases.html', {
        'labels': labels,
        'values': values,
        'purchases_by_supplier': purchases_by_supplier,
    })
