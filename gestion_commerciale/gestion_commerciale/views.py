from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from django.shortcuts import render
from django.db.models import Sum, Count, Q, F, Case, When, Value, IntegerField, DecimalField
from django.db.models.functions import Coalesce
from datetime import timedelta

# Import models
from sales.models import Sale
from products.models import Product
from clients.models import Client
from inventory.models import Stock, StockMovement

@login_required
def dashboard_view(request):
    today = now().date()
    yesterday = today - timedelta(days=1)
    start_of_month = today.replace(day=1)

    # Calculate daily sales
    daily_sales = Sale.objects.filter(date__date=today).aggregate(
        total=Sum('total_amount'))['total'] or 0
    yesterday_sales = Sale.objects.filter(date__date=yesterday).aggregate(
        total=Sum('total_amount'))['total'] or 0
    
    # Calculate sales trend
    sales_trend = 0
    if yesterday_sales > 0:
        sales_trend = ((daily_sales - yesterday_sales) / yesterday_sales) * 100

    # Products statistics
    total_products = Product.objects.count()
    
    # Calculate current stock levels for each product using Stock model
    products_with_stock = Product.objects.annotate(
        current_stock=Coalesce(
            Sum('stock_entries__quantity'),
            Value(0, output_field=DecimalField())
        )
    )

    # Set low stock threshold
    low_stock_threshold = 10  # You can adjust this value
    
    # Get products with low stock
    low_stock_products = products_with_stock.filter(
        current_stock__lte=low_stock_threshold
    ).order_by('current_stock')[:6]
    
    low_stock_count = products_with_stock.filter(
        current_stock__lte=low_stock_threshold
    ).count()

    # Clients statistics
    total_clients = Client.objects.count()
    new_clients = Client.objects.filter(created_at__gte=start_of_month).count()

    # Debts statistics
    debts_data = Sale.objects.filter(
        amount_paid__lt=F('total_amount')
    ).aggregate(
        total_debts=Sum(F('total_amount') - F('amount_paid')),
        debts_count=Count('client', distinct=True)
    )

    # Recent orders
    recent_orders = Sale.objects.select_related('client').order_by('-date')[:5]

    context = {
        "now": now(),
        
        # Sales statistics
        "daily_sales": daily_sales,
        "sales_trend": round(sales_trend, 1),
        
        # Products statistics
        "total_products": total_products,
        "low_stock": low_stock_count,
        "low_stock_products": low_stock_products,
        
        # Clients statistics
        "total_clients": total_clients,
        "new_clients": new_clients,
        
        # Debts statistics
        "total_debts": debts_data.get('total_debts', 0) or 0,
        "debts_count": debts_data.get('debts_count', 0),
        
        # Recent activity
        "recent_orders": recent_orders,
    }
    
    return render(request, "dashboard/dashboard.html", context)
