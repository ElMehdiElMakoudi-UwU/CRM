from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncDate
from .models import Order, OrderItem, SalesMetric, ProductPerformance, SalesRepPerformance
from products.models import Product, Category
from clients.models import Client
from django.http import JsonResponse, FileResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
import json
import os
from django.conf import settings
from datetime import datetime, timedelta

# Create your views here.

@login_required
def dashboard(request):
    # Get today's date range
    today = timezone.now().date()
    today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    today_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
    
    # Get today's statistics
    today_orders = Order.objects.filter(created_at__range=(today_start, today_end))
    today_orders_count = today_orders.count()
    today_revenue = today_orders.aggregate(total=Sum('total_amount'))['total'] or 0
    today_items_sold = OrderItem.objects.filter(order__created_at__range=(today_start, today_end)).aggregate(total=Sum('quantity'))['total'] or 0
    
    # Get recent orders
    recent_orders = Order.objects.all().order_by('-created_at')[:5]
    
    context = {
        'today_orders_count': today_orders_count,
        'today_revenue': today_revenue,
        'today_items_sold': today_items_sold,
        'recent_orders': recent_orders,
    }
    
    return render(request, 'mobile_pos/dashboard.html', context)

@login_required
def order_list(request):
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'mobile_pos/order_list.html', {'orders': orders})

@login_required
def client_history(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    
    # Get client's orders
    orders = Order.objects.filter(client_name=client.name).order_by('-created_at')
    recent_orders = orders[:5]
    
    # Calculate statistics
    total_orders = orders.count()
    total_amount = orders.aggregate(total=Sum('total_amount'))['total'] or 0
    total_items = OrderItem.objects.filter(order__in=orders).aggregate(total=Sum('quantity'))['total'] or 0
    
    # Get frequently ordered products
    frequent_products = Product.objects.filter(
        orderitem__order__in=orders
    ).annotate(
        order_count=Count('orderitem')
    ).order_by('-order_count')[:5]
    
    context = {
        'client': client,
        'recent_orders': recent_orders,
        'total_orders': total_orders,
        'total_amount': total_amount,
        'total_items': total_items,
        'frequent_products': frequent_products,
    }
    
    return render(request, 'mobile_pos/client_history.html', context)

@login_required
def create_order(request):
    products = Product.objects.all()
    clients = Client.objects.all().order_by('name')
    categories = Category.objects.all()
    
    # Get frequently ordered products (top 4 in the last 30 days)
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    frequent_products = Product.objects.filter(
        orderitem__order__created_at__gte=thirty_days_ago
    ).annotate(
        order_count=Count('orderitem')
    ).order_by('-order_count')[:4]
    
    # Handle reorder from previous order
    reorder_id = request.GET.get('reorder')
    initial_data = {}
    if reorder_id:
        try:
            previous_order = Order.objects.get(id=reorder_id)
            initial_data['client_id'] = previous_order.client.id if previous_order.client else None
            initial_data['client_name'] = previous_order.client_name
            initial_data['client_contact'] = previous_order.client_contact
            initial_data['notes'] = previous_order.notes
            initial_data['items'] = [
                {'product_id': item.product.id, 'quantity': item.quantity}
                for item in previous_order.items.all()
            ]
        except Order.DoesNotExist:
            messages.error(request, "Commande non trouvée.")
    
    # Handle quick reorder of single product
    product_id = request.GET.get('product_id')
    client_id = request.GET.get('client_id')
    if product_id and client_id:
        try:
            client = Client.objects.get(id=client_id)
            initial_data['client_id'] = client.id
            initial_data['client_name'] = client.name
            initial_data['client_contact'] = client.phone or client.email or ''
            initial_data['items'] = [
                {'product_id': product_id, 'quantity': 1}
            ]
        except Client.DoesNotExist:
            messages.error(request, "Client non trouvé.")
    
    if request.method == 'POST':
        client_id = request.POST.get('client_id')
        client_name = request.POST.get('client_name')
        client_contact = request.POST.get('client_contact')
        notes = request.POST.get('notes')
        
        # If a client was selected, use their information
        if client_id:
            client = get_object_or_404(Client, id=client_id)
            client_name = client.name
            client_contact = client.phone or client.email or ''
        
        order = Order.objects.create(
            client_name=client_name,
            client_contact=client_contact,
            notes=notes
        )
        
        # Process order items
        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')
        
        total_amount = 0
        for product_id, quantity in zip(product_ids, quantities):
            if product_id and quantity:
                product = get_object_or_404(Product, id=product_id)
                quantity = int(quantity)
                if quantity > 0:
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=quantity,
                        unit_price=product.selling_price,
                        subtotal=product.selling_price * quantity
                    )
                    total_amount += product.selling_price * quantity
        
        order.total_amount = total_amount
        order.save()
        messages.success(request, 'Order created successfully!')
        return redirect('mobile_pos:order_detail', order_id=order.id)
    
    context = {
        'products': products,
        'clients': clients,
        'categories': categories,
        'frequent_products': frequent_products,
        'initial_data': initial_data,
    }
    
    return render(request, 'mobile_pos/create_order.html', context)

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'mobile_pos/order_detail.html', {'order': order})

@login_required
def update_order_status(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')
        if new_status in dict(Order.ORDER_STATUS):
            order.status = new_status
            order.save()
            messages.success(request, 'Order status updated successfully!')
        return redirect('mobile_pos:order_detail', order_id=order.id)

@require_http_methods(["POST"])
def sync_order(request):
    try:
        data = json.loads(request.body)
        
        # Create order
        order = Order.objects.create(
            client_name=data['client_name'],
            total_amount=data['total_amount'],
            created_at=data['created_at']
        )

        # Create order items
        for item in data['items']:
            OrderItem.objects.create(
                order=order,
                product_id=item['product_id'],
                quantity=item['quantity'],
                price=item['price']
            )

        return JsonResponse({
            'status': 'success',
            'order_id': order.id
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@ensure_csrf_cookie
def offline_page(request):
    return render(request, 'mobile_pos/offline.html')

def serve_service_worker(request):
    file_path = os.path.join(settings.STATIC_ROOT, 'mobile_pos', 'sw.js')
    return FileResponse(
        open(file_path, 'rb'),
        content_type='application/javascript'
    )

@require_http_methods(["GET"])
def api_products(request):
    products = Product.objects.all().values(
        'id', 'name', 'price', 'category__name', 'stock'
    )
    return JsonResponse(list(products), safe=False)

@login_required
def analytics_dashboard(request):
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Calculate metrics for the last 30 days
    daily_metrics = SalesMetric.objects.filter(
        date__range=[start_date, end_date]
    ).order_by('date')
    
    # Calculate total metrics
    total_metrics = {
        'total_sales': sum(metric.total_sales for metric in daily_metrics),
        'total_orders': sum(metric.total_orders for metric in daily_metrics),
        'avg_order_value': sum(metric.total_sales for metric in daily_metrics) / 
                          sum(metric.total_orders for metric in daily_metrics) 
                          if sum(metric.total_orders for metric in daily_metrics) > 0 else 0
    }
    
    # Get top performing products
    top_products = ProductPerformance.objects.filter(
        date__range=[start_date, end_date]
    ).values('product__name').annotate(
        total_units=Sum('units_sold'),
        total_revenue=Sum('revenue')
    ).order_by('-total_revenue')[:5]
    
    # Get sales rep performance
    sales_rep_performance = SalesRepPerformance.objects.filter(
        date__range=[start_date, end_date]
    ).values('user__username').annotate(
        total_sales=Sum('total_sales'),
        total_orders=Sum('orders_processed'),
        avg_conversion=Avg('conversion_rate')
    ).order_by('-total_sales')
    
    # Prepare chart data
    chart_data = {
        'dates': [metric.date.strftime('%Y-%m-%d') for metric in daily_metrics],
        'sales': [float(metric.total_sales) for metric in daily_metrics],
        'orders': [metric.total_orders for metric in daily_metrics],
        'avg_values': [float(metric.average_order_value) for metric in daily_metrics]
    }
    
    context = {
        'total_metrics': total_metrics,
        'top_products': top_products,
        'sales_rep_performance': sales_rep_performance,
        'chart_data': chart_data,
    }
    
    return render(request, 'mobile_pos/analytics_dashboard.html', context)

@login_required
def product_performance(request):
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    products = ProductPerformance.objects.filter(
        date__range=[start_date, end_date]
    ).values('product__name', 'product__category__name').annotate(
        total_units=Sum('units_sold'),
        total_revenue=Sum('revenue'),
        daily_avg_units=Avg('units_sold'),
        daily_avg_revenue=Avg('revenue')
    ).order_by('-total_revenue')
    
    # Calculate category performance
    categories = ProductPerformance.objects.filter(
        date__range=[start_date, end_date]
    ).values('product__category__name').annotate(
        total_revenue=Sum('revenue'),
        total_units=Sum('units_sold')
    ).order_by('-total_revenue')
    
    context = {
        'products': products,
        'categories': categories,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'mobile_pos/product_performance.html', context)

@login_required
def sales_rep_analytics(request):
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    performance = SalesRepPerformance.objects.filter(
        date__range=[start_date, end_date]
    ).values('user__username').annotate(
        total_sales=Sum('total_sales'),
        total_orders=Sum('orders_processed'),
        avg_conversion=Avg('conversion_rate'),
        daily_avg_sales=Avg('total_sales'),
        daily_avg_orders=Avg('orders_processed')
    ).order_by('-total_sales')
    
    # Get daily performance for charts
    daily_performance = SalesRepPerformance.objects.filter(
        date__range=[start_date, end_date]
    ).values('date', 'user__username').annotate(
        daily_sales=Sum('total_sales'),
        daily_orders=Count('orders_processed')
    ).order_by('date', 'user__username')
    
    context = {
        'performance': performance,
        'daily_performance': daily_performance,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'mobile_pos/sales_rep_analytics.html', context)
