from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncDate
from decimal import Decimal
from .models import Order, OrderItem, SalesMetric, ProductPerformance, SalesRepPerformance, InventoryRequest, InventoryRequestItem, InventoryLoadRequest, SellerInventory
from products.models import Product, Category
from clients.models import Client
from clients.forms import ClientForm
from sales.models import Sale, SaleItem
from inventory.models import Warehouse, Stock, StockMovement
from operations.models import Seller
from datetime import datetime
from django.http import JsonResponse, FileResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from users.decorators import role_required
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
    
    # Get seller for current user (if exists)
    seller = None
    if hasattr(request.user, 'seller_profile'):
        seller = request.user.seller_profile
    else:
        try:
            seller = Seller.objects.get(user=request.user)
        except Seller.DoesNotExist:
            pass
    
    # Get today's statistics from Sale model (filtered by current user)
    today_sales = Sale.objects.filter(
        user=request.user,
        date__range=(today_start, today_end)
    )
    today_orders_count = today_sales.count()
    today_revenue = today_sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    today_items_sold = SaleItem.objects.filter(
        sale__user=request.user,
        sale__date__range=(today_start, today_end)
    ).aggregate(total=Sum('quantity'))['total'] or Decimal('0')
    
    # Get recent sales (filtered by current user)
    recent_orders = Sale.objects.filter(user=request.user).order_by('-date')[:5]
    
    context = {
        'today_orders_count': today_orders_count,
        'today_revenue': today_revenue,
        'today_items_sold': int(today_items_sold) if today_items_sold else 0,
        'recent_orders': recent_orders,
    }
    
    return render(request, 'mobile_pos/dashboard.html', context)

@login_required
def order_list(request):
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'mobile_pos/order_list.html', {'orders': orders})

@login_required
def client_history(request, client_id):
    # Filter clients based on user role
    user_role = request.user.profile.role if hasattr(request.user, 'profile') else None
    if user_role in ['manager', 'admin']:
        client = get_object_or_404(Client, id=client_id)
    else:
        # Sales reps can only see clients they created
        client = get_object_or_404(Client, id=client_id, created_by=request.user)
    
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
    # Use STATICFILES_DIRS or STATIC_ROOT, fallback to a default path
    if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT:
        file_path = os.path.join(settings.STATIC_ROOT, 'mobile_pos', 'sw.js')
    else:
        # Fallback to static files directory
        file_path = os.path.join(settings.BASE_DIR, 'mobile_pos', 'static', 'mobile_pos', 'sw.js')
    
    if os.path.exists(file_path):
        return FileResponse(
            open(file_path, 'rb'),
            content_type='application/javascript'
        )
    else:
        # Return empty service worker if file doesn't exist
        return HttpResponse("// Service worker not configured", content_type='application/javascript')

@require_http_methods(["GET"])
def api_products(request):
    products = Product.objects.all().values(
        'id', 'name', 'selling_price', 'category__name'
    )
    return JsonResponse(list(products), safe=False)

@login_required
@require_http_methods(["GET"])
def api_product_by_barcode(request):
    """API endpoint to get product by barcode, checking seller inventory"""
    barcode = request.GET.get('barcode', '').strip()
    
    if not barcode:
        return JsonResponse({
            'status': 'error',
            'message': 'Code-barres requis'
        }, status=400)
    
    try:
        # Get seller for current user
        seller = None
        if hasattr(request.user, 'seller_profile'):
            seller = request.user.seller_profile
        else:
            try:
                seller = Seller.objects.get(user=request.user)
            except Seller.DoesNotExist:
                pass
        
        # Find product by barcode
        product = Product.objects.filter(barcode=barcode, is_active=True).first()
        
        if not product:
            return JsonResponse({
                'status': 'error',
                'message': 'Produit non trouvé avec ce code-barres'
            }, status=404)
        
        # Check if product is in seller's inventory
        available_quantity = Decimal('0')
        if seller:
            inventory_item = SellerInventory.objects.filter(
                seller=seller,
                product=product
            ).first()
            if inventory_item:
                available_quantity = inventory_item.quantity
        
        return JsonResponse({
            'status': 'success',
            'product': {
                'id': product.id,
                'name': product.name,
                'barcode': product.barcode,
                'selling_price': str(product.selling_price),
                'available_quantity': str(available_quantity),
                'in_stock': available_quantity > 0
            }
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

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


# =========================
# INVENTORY REQUEST VIEWS
# =========================

@login_required
def inventory_request_list(request):
    """List all inventory requests for the current sales rep"""
    requests = InventoryRequest.objects.filter(sales_rep=request.user).order_by('-created_at')
    return render(request, 'mobile_pos/inventory_request_list.html', {
        'requests': requests
    })


@login_required
def inventory_request_create(request):
    """Create a new inventory request"""
    products = Product.objects.all().order_by('name')
    warehouses = Warehouse.objects.filter(is_active=True)
    
    if request.method == 'POST':
        warehouse_id = request.POST.get('warehouse')
        notes = request.POST.get('notes', '')
        
        # Create the request
        inventory_request = InventoryRequest.objects.create(
            sales_rep=request.user,
            warehouse_id=warehouse_id if warehouse_id else None,
            notes=notes
        )
        
        # Process items
        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')
        item_notes = request.POST.getlist('item_notes[]')
        
        for product_id, quantity, item_note in zip(product_ids, quantities, item_notes):
            if product_id and quantity and int(quantity) > 0:
                InventoryRequestItem.objects.create(
                    request=inventory_request,
                    product_id=product_id,
                    quantity=int(quantity),
                    notes=item_note if item_note else None
                )
        
        messages.success(request, 'Demande d\'inventaire créée avec succès!')
        return redirect('mobile_pos:inventory_request_detail', request_id=inventory_request.id)
    
    context = {
        'products': products,
        'warehouses': warehouses,
    }
    return render(request, 'mobile_pos/inventory_request_create.html', context)


@login_required
def inventory_request_detail(request, request_id):
    """View details of an inventory request"""
    inventory_request = get_object_or_404(InventoryRequest, id=request_id, sales_rep=request.user)
    return render(request, 'mobile_pos/inventory_request_detail.html', {
        'request': inventory_request
    })


# =========================
# CLIENT MANAGEMENT VIEWS (MOBILE)
# =========================

@login_required
def client_list_mobile(request):
    """Mobile-friendly client list"""
    query = request.GET.get('q', '')
    
    # Filter clients based on user role
    # Managers and admins see all clients, sales reps only see their own
    user_role = request.user.profile.role if hasattr(request.user, 'profile') else None
    if user_role in ['manager', 'admin']:
        clients = Client.objects.all()
    else:
        # Sales reps only see clients they created
        clients = Client.objects.filter(created_by=request.user)
    
    if query:
        clients = clients.filter(
            Q(name__icontains=query) | 
            Q(phone__icontains=query) | 
            Q(email__icontains=query)
        )
    
    clients = clients.order_by('name')[:50]  # Limit for mobile performance
    return render(request, 'mobile_pos/client_list.html', {
        'clients': clients,
        'query': query
    })


@login_required
def client_create_mobile(request):
    """Mobile-friendly client creation"""
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save(commit=False)
            client.created_by = request.user
            client.save()
            messages.success(request, f'Client {client.name} créé avec succès!')
            return redirect('mobile_pos:client_list_mobile')
    else:
        form = ClientForm()
    
    return render(request, 'mobile_pos/client_create.html', {
        'form': form
    })


@login_required
@require_http_methods(["GET"])
def api_search_clients(request):
    """API endpoint to search clients with history and stats"""
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return JsonResponse({
            'status': 'error',
            'message': 'Veuillez saisir au moins 2 caractères'
        }, status=400)
    
    try:
        # Filter clients based on user role
        user_role = request.user.profile.role if hasattr(request.user, 'profile') else None
        if user_role in ['manager', 'admin']:
            clients_qs = Client.objects.all()
        else:
            clients_qs = Client.objects.filter(created_by=request.user)
        
        # Search by name or phone
        clients = clients_qs.filter(
            Q(name__icontains=query) | 
            Q(phone__icontains=query)
        )[:10]  # Limit to 10 results
        
        results = []
        for client in clients:
            # Get last sale
            last_sale = Sale.objects.filter(client=client).order_by('-date').first()
            
            # Calculate total spent
            total_spent = Sale.objects.filter(client=client).aggregate(
                total=Sum('total_amount')
            )['total'] or Decimal('0')
            
            # Get favorite products (most purchased by quantity)
            favorite_products = Product.objects.filter(
                saleitem__sale__client=client
            ).annotate(
                purchase_count=Sum('saleitem__quantity')
            ).filter(purchase_count__gt=0).order_by('-purchase_count')[:3]
            
            results.append({
                'id': client.id,
                'name': client.name,
                'phone': client.phone or '',
                'email': client.email or '',
                'last_order_date': last_sale.date.strftime('%d/%m/%Y %H:%M') if last_sale else None,
                'total_spent': str(total_spent),
                'total_orders': Sale.objects.filter(client=client).count(),
                'favorite_products': [
                    {
                        'name': p.name,
                        'purchase_count': int(p.purchase_count or 0)
                    } for p in favorite_products if p.purchase_count
                ]
            })
        
        return JsonResponse({
            'status': 'success',
            'clients': results
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def api_create_client(request):
    """API endpoint to create a client via AJAX"""
    try:
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip() or None
        email = request.POST.get('email', '').strip() or None
        address = request.POST.get('address', '').strip() or None
        segment_id = request.POST.get('segment', '').strip() or None
        
        if not name:
            return JsonResponse({
                'status': 'error',
                'message': 'Le nom du client est requis'
            }, status=400)
        
        # Create client
        client = Client.objects.create(
            name=name,
            phone=phone,
            email=email,
            address=address,
            segment_id=segment_id if segment_id else None,
            created_by=request.user
        )
        
        return JsonResponse({
            'status': 'success',
            'message': f'Client {client.name} créé avec succès!',
            'client': {
                'id': client.id,
                'name': client.name,
                'phone': client.phone or '',
                'email': client.email or '',
            }
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@login_required
def client_outstanding_debt(request):
    """Track clients with outstanding debt for the current sales rep"""
    # Get all sales with outstanding debt for the current user
    sales_with_debt = Sale.objects.filter(
        user=request.user,
        is_credit=True
    ).select_related('client').order_by('-date')
    
    # Group by client and calculate total outstanding debt
    client_debt_dict = {}
    for sale in sales_with_debt:
        if sale.client:
            client_id = sale.client.id
            balance_due = sale.get_balance_due()
            
            if client_id not in client_debt_dict:
                client_debt_dict[client_id] = {
                    'client': sale.client,
                    'total_debt': Decimal('0'),
                    'sales': []
                }
            
            client_debt_dict[client_id]['total_debt'] += balance_due
            client_debt_dict[client_id]['sales'].append({
                'sale': sale,
                'balance_due': balance_due,
                'date': sale.date
            })
    
    # Convert to list and sort by total debt (highest first)
    clients_with_debt = sorted(
        client_debt_dict.values(),
        key=lambda x: x['total_debt'],
        reverse=True
    )
    
    # Calculate total outstanding debt
    total_outstanding = sum(client['total_debt'] for client in clients_with_debt)
    
    context = {
        'clients_with_debt': clients_with_debt,
        'total_outstanding': total_outstanding,
        'total_clients': len(clients_with_debt)
    }
    
    return render(request, 'mobile_pos/client_outstanding_debt.html', context)


# =========================
# SALES VIEWS (MOBILE)
# =========================

@login_required
def sale_create_mobile(request):
    """Mobile-friendly sale creation"""
    # Get seller's inventory - only show products they have in stock
    seller = None
    if hasattr(request.user, 'seller_profile'):
        seller = request.user.seller_profile
    else:
        try:
            seller = Seller.objects.get(user=request.user)
        except Seller.DoesNotExist:
            pass
    
    # Get products that the seller has in inventory (stock > 0)
    if seller:
        seller_inventory = SellerInventory.objects.filter(
            seller=seller,
            quantity__gt=0
        ).select_related('product')
        products = [item.product for item in seller_inventory]
        # Create a dict for quick lookup of available quantities
        inventory_dict = {item.product.id: item.quantity for item in seller_inventory}
    else:
        products = []
        inventory_dict = {}
        messages.warning(request, "Vous n'êtes pas associé à un vendeur. Impossible de créer une vente.")
    
    # Filter clients based on user role
    # Managers and admins see all clients, sales reps only see their own
    user_role = request.user.profile.role if hasattr(request.user, 'profile') else None
    if user_role in ['manager', 'admin']:
        clients = Client.objects.all().order_by('name')
    else:
        # Sales reps only see clients they created
        clients = Client.objects.filter(created_by=request.user).order_by('name')
    
    warehouses = Warehouse.objects.filter(is_active=True)
    categories = Category.objects.all()
    
    if request.method == 'POST':
        if not seller:
            messages.error(request, 'Vous n\'êtes pas associé à un vendeur.')
            return redirect('mobile_pos:sale_create_mobile')
        
        client_id = request.POST.get('client_id')
        notes = request.POST.get('notes', '')
        amount_paid = Decimal(request.POST.get('amount_paid', 0))
        
        # Get default warehouse (not used for stock check, but required by Sale model)
        warehouse = Warehouse.objects.filter(is_active=True).first()
        
        # Get or create client
        if client_id:
            client = get_object_or_404(Client, id=client_id)
        else:
            # Create new client on the fly
            client_name = request.POST.get('client_name', '').strip()
            client_phone = request.POST.get('client_phone', '').strip()
            if client_name:
                client, created = Client.objects.get_or_create(
                    name=client_name,
                    defaults={
                        'phone': client_phone,
                        'created_by': request.user
                    }
                )
            else:
                messages.error(request, 'Veuillez sélectionner ou créer un client.')
                return redirect('mobile_pos:sale_create_mobile')
        
        # Create sale with initial total_amount of 0
        sale = Sale.objects.create(
            user=request.user,
            client=client,
            warehouse=warehouse,
            notes=notes,
            amount_paid=amount_paid,
            total_amount=Decimal('0')  # Set initial total to 0, will be updated after items are added
        )
        
        # Process items and deduct from seller inventory
        if not seller:
            messages.error(request, 'Vous n\'êtes pas associé à un vendeur.')
            return redirect('mobile_pos:sale_create_mobile')
        
        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')
        
        total_amount = Decimal('0')
        items_to_create = []
        inventory_updates = {}
        
        for product_id, quantity in zip(product_ids, quantities):
            if product_id and quantity and int(quantity) > 0:
                product = get_object_or_404(Product, id=product_id)
                qty = int(quantity)
                
                # Check seller's inventory availability
                seller_inventory_item = SellerInventory.objects.filter(
                    seller=seller,
                    product=product
                ).first()
                
                available = seller_inventory_item.quantity if seller_inventory_item else Decimal('0')
                
                if available < qty:
                    messages.warning(request, f'Stock insuffisant pour {product.name}. Disponible: {available}')
                    qty = min(qty, int(available))
                
                if qty > 0:
                    unit_price = product.selling_price
                    items_to_create.append({
                        'sale': sale,
                        'product': product,
                        'quantity': qty,
                        'unit_price': unit_price
                    })
                    total_amount += unit_price * qty
                    
                    # Track inventory deduction
                    if product.id not in inventory_updates:
                        inventory_updates[product.id] = {
                            'item': seller_inventory_item,
                            'quantity': Decimal('0')
                        }
                    inventory_updates[product.id]['quantity'] += Decimal(str(qty))
        
        if total_amount == 0:
            messages.error(request, 'Veuillez ajouter au moins un produit à la vente.')
            sale.delete()
            return redirect('mobile_pos:sale_create_mobile')
        
        # Create sale items
        for item_data in items_to_create:
            SaleItem.objects.create(**item_data)
        
        # Deduct from seller inventory
        for product_id, update_data in inventory_updates.items():
            inventory_item = update_data['item']
            if not inventory_item:
                # This shouldn't happen if we're only showing products in stock, but handle it anyway
                continue
            
            new_quantity = max(
                Decimal(str(inventory_item.quantity)) - update_data['quantity'],
                Decimal('0')
            )
            inventory_item.quantity = new_quantity
            inventory_item.save()
            
            # If quantity reaches 0, we could optionally delete the record, but keeping it is fine
        
        sale.total_amount = total_amount
        sale.save()
        
        messages.success(request, f'Vente #{sale.id} créée avec succès!')
        return redirect('mobile_pos:sale_detail_mobile', sale_id=sale.id)
    
    # Prepare products with inventory info for template
    products_with_stock = []
    for product in products:
        available = inventory_dict.get(product.id, Decimal('0'))
        products_with_stock.append({
            'product': product,
            'available_stock': available
        })
    
    # Get client segments for the create client modal
    from clients.models import ClientSegment
    segments = ClientSegment.objects.all().order_by('name')
    
    context = {
        'products_with_stock': products_with_stock,
        'clients': clients,
        'warehouses': warehouses,
        'categories': categories,
        'seller': seller,
        'segments': segments,
    }
    return render(request, 'mobile_pos/sale_create.html', context)


@login_required
def sale_detail_mobile(request, sale_id):
    """Mobile-friendly sale detail view"""
    sale = get_object_or_404(Sale, id=sale_id, user=request.user)
    return render(request, 'mobile_pos/sale_detail.html', {
        'sale': sale
    })


@login_required
def sale_list_mobile(request):
    """Mobile-friendly sale list"""
    sales = Sale.objects.filter(user=request.user).order_by('-date')[:50]
    return render(request, 'mobile_pos/sale_list.html', {
        'sales': sales
    })


# =========================
# INVENTORY LOAD/UNLOAD VIEWS (MOBILE)
# =========================

@login_required
def mobile_load_inventory(request):
    """Sales rep requests inventory to load"""
    seller = None
    # Try to get seller using the related_name
    if hasattr(request.user, 'seller_profile'):
        seller = request.user.seller_profile
    else:
        # Fallback: try direct query
        try:
            seller = Seller.objects.get(user=request.user)
        except Seller.DoesNotExist:
            pass
    
    if not seller:
        messages.error(request, "Vous n'êtes pas associé à un vendeur. Veuillez contacter l'administrateur.")
        return redirect('mobile_pos:dashboard')
    
    products = Product.objects.filter(is_active=True).order_by('name')
    
    # Get warehouse stock information
    warehouse = Warehouse.objects.filter(is_active=True).first()
    product_stock = {}
    if warehouse:
        for product in products:
            stock = Stock.objects.filter(product=product, warehouse=warehouse).first()
            product_stock[product.id] = stock.quantity if stock else Decimal('0')
    else:
        for product in products:
            product_stock[product.id] = Decimal('0')
    
    selected_date_str = request.GET.get('date') or request.POST.get('date')
    selected_date = timezone.now().date()
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Format de date invalide.")
            selected_date = timezone.now().date()
    
    if request.method == "POST":
        created_any = False
        for product in products:
            try:
                qty = int(request.POST.get(f"quantity_{product.id}", 0))
            except ValueError:
                qty = 0
            
            if qty > 0:
                # Check if there's already a pending request
                exists = InventoryLoadRequest.objects.filter(
                    seller=seller,
                    product=product,
                    date=selected_date,
                    validated=False
                ).exists()
                
                if not exists:
                    InventoryLoadRequest.objects.create(
                        seller=seller,
                        product=product,
                        requested_quantity=qty,
                        date=selected_date
                    )
                    created_any = True
        
        if created_any:
            messages.success(request, "Demande envoyée pour validation.")
        else:
            messages.info(request, "Aucune nouvelle demande envoyée.")
        return redirect('mobile_pos:mobile_inventory_status')
    
    # Get existing requests for display
    existing_requests = InventoryLoadRequest.objects.filter(
        seller=seller, 
        date=selected_date, 
        validated=False
    ).select_related('product')
    
    # Prepare products with stock info for template
    products_with_stock = []
    for product in products:
        products_with_stock.append({
            'product': product,
            'available_stock': product_stock.get(product.id, Decimal('0'))
        })
    
    return render(request, "mobile_pos/load_inventory.html", {
        "products_with_stock": products_with_stock,
        "selected_date": selected_date.strftime('%Y-%m-%d'),
        "existing_requests": existing_requests,
        "warehouse": warehouse,
    })


@login_required
@role_required(allowed_roles=['manager', 'admin'])
def manager_log_unload(request):
    """Manager logs inventory unload for a sales rep"""
    sellers = Seller.objects.all().order_by('name')
    selected_seller_id = request.GET.get('seller_id')
    selected_seller = None
    
    if selected_seller_id:
        try:
            selected_seller = Seller.objects.get(id=selected_seller_id)
        except Seller.DoesNotExist:
            messages.error(request, "Vendeur introuvable.")
    
    if request.method == "POST":
        seller_id = request.POST.get('seller_id')
        if not seller_id:
            messages.error(request, "Veuillez sélectionner un vendeur.")
            return redirect('mobile_pos:manager_log_unload')
        
        try:
            seller = Seller.objects.get(id=seller_id)
        except Seller.DoesNotExist:
            messages.error(request, "Vendeur introuvable.")
            return redirect('mobile_pos:manager_log_unload')
        
        products = Product.objects.filter(is_active=True).order_by('name')
        unloads_logged = 0
        
        for product in products:
            try:
                unload_qty = Decimal(request.POST.get(f"unload_{product.id}", 0))
            except (ValueError, TypeError):
                unload_qty = Decimal('0')
            
            if unload_qty > 0:
                inventory = SellerInventory.objects.filter(seller=seller, product=product).first()
                if inventory:
                    if inventory.quantity < unload_qty:
                        messages.warning(request, f"Quantité à décharger ({unload_qty}) supérieure au stock disponible ({inventory.quantity}) pour {product.name}. Déchargement limité au stock disponible.")
                        unload_qty = inventory.quantity
                    
                    inventory.quantity = max(Decimal(str(inventory.quantity)) - unload_qty, Decimal('0'))
                    inventory.save()
                    
                    # Create stock movement record
                    warehouse = Warehouse.objects.filter(is_active=True).first()
                    if warehouse:
                        StockMovement.objects.create(
                            product=product,
                            warehouse=warehouse,
                            movement_type='in',  # Inventory returned to warehouse
                            quantity=unload_qty,
                            source=f'Déchargement vendeur: {seller.name} (Géré par {request.user.username})',
                            user=request.user
                        )
                    
                    unloads_logged += 1
        
        if unloads_logged > 0:
            messages.success(request, f"Déchargement de {unloads_logged} produit(s) enregistré avec succès pour {seller.name}.")
        else:
            messages.info(request, "Aucun déchargement enregistré.")
        
        return redirect(f"{reverse('mobile_pos:manager_log_unload')}?seller_id={seller.id}")
    
    # GET request - show form
    inventory_data = []
    if selected_seller:
        inventory_data = SellerInventory.objects.filter(
            seller=selected_seller,
            quantity__gt=0
        ).select_related("product").order_by("product__name")
    
    context = {
        "sellers": sellers,
        "selected_seller": selected_seller,
        "inventory": inventory_data,
    }
    
    return render(request, "mobile_pos/manager_log_unload.html", context)


@login_required
def mobile_inventory_status(request):
    """View current inventory status and pending requests"""
    seller = None
    # Try to get seller using the related_name
    if hasattr(request.user, 'seller_profile'):
        seller = request.user.seller_profile
    else:
        # Fallback: try direct query
        try:
            seller = Seller.objects.get(user=request.user)
        except Seller.DoesNotExist:
            # Allow viewing the page even without a seller profile
            pass
        except Seller.MultipleObjectsReturned:
            # If multiple sellers exist, get the first one
            seller = Seller.objects.filter(user=request.user).first()
    
    if seller:
        # Current inventory
        current_inventory = SellerInventory.objects.filter(seller=seller).select_related("product")
        
        # Pending requests
        pending_requests = InventoryLoadRequest.objects.filter(
            seller=seller,
            validated=False
        ).select_related('product').order_by('-date', '-created_at')
        
        # Recent validated requests
        recent_validated = InventoryLoadRequest.objects.filter(
            seller=seller,
            validated=True
        ).select_related('product').order_by('-validated_at')[:10]
    else:
        current_inventory = SellerInventory.objects.none()
        pending_requests = InventoryLoadRequest.objects.none()
        recent_validated = InventoryLoadRequest.objects.none()
    
    return render(request, "mobile_pos/inventory_status.html", {
        "seller": seller,
        "current_inventory": current_inventory,
        "pending_requests": pending_requests,
        "recent_validated": recent_validated,
    })


@login_required
def validate_inventory_requests(request):
    """Manager validates and modifies inventory load requests"""
    # Check if user is staff/manager (adjust based on your permission system)
    if not request.user.is_staff:
        messages.error(request, "Vous n'avez pas les permissions nécessaires.")
        return redirect('mobile_pos:dashboard')
    
    selected_date_str = request.GET.get("date")
    selected_date = timezone.now().date()
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Format de date invalide.")
            selected_date = timezone.now().date()
    
    requests = InventoryLoadRequest.objects.filter(
        date=selected_date, 
        validated=False
    ).select_related('seller', 'product').order_by('seller', 'product')
    
    # Get warehouse stock for each product
    warehouse = Warehouse.objects.filter(is_active=True).first()
    warehouse_stock = {}
    if warehouse:
        for req in requests:
            if req.product not in warehouse_stock:
                stock = Stock.objects.filter(product=req.product, warehouse=warehouse).first()
                warehouse_stock[req.product] = stock.quantity if stock else Decimal('0')
    
    if request.method == "POST":
        validated_count = 0
        errors = []
        
        for req in requests:
            approved_qty_str = request.POST.get(f"approved_quantity_{req.id}")
            notes = request.POST.get(f"notes_{req.id}", "").strip()
            
            if approved_qty_str:
                try:
                    approved_qty = int(approved_qty_str)
                    
                    # Check if this request should be approved
                    if f"approve_{req.id}" in request.POST and approved_qty > 0:
                        # Check warehouse stock availability
                        available_stock = warehouse_stock.get(req.product, Decimal('0'))
                        
                        if approved_qty > available_stock:
                            errors.append(f"{req.product.name}: Stock insuffisant. Disponible: {available_stock}, Demandé: {approved_qty}")
                            continue
                        
                        # Update the request with approved quantity
                        req.approved_quantity = approved_qty
                        req.notes = notes if notes else None
                        req.validated = True
                        req.validated_by = request.user
                        req.validated_at = timezone.now()
                        req.save()
                        
                        # Update seller inventory
                        seller_inventory, _ = SellerInventory.objects.get_or_create(
                            seller=req.seller,
                            product=req.product,
                            defaults={"quantity": Decimal('0')}
                        )
                        seller_inventory.quantity = Decimal(str(seller_inventory.quantity)) + Decimal(str(approved_qty))
                        seller_inventory.save()
                        
                        # Deduct from warehouse stock
                        if warehouse:
                            stock, _ = Stock.objects.get_or_create(
                                product=req.product,
                                warehouse=warehouse,
                                defaults={"quantity": Decimal('0')}
                            )
                            stock.quantity = max(Decimal(str(stock.quantity)) - Decimal(str(approved_qty)), Decimal('0'))
                            stock.save()
                            
                            # Create stock movement record
                            StockMovement.objects.create(
                                product=req.product,
                                warehouse=warehouse,
                                movement_type='out',
                                quantity=Decimal(str(approved_qty)),
                                source=f'chargement_vendeur: {req.seller.name}',
                                user=request.user
                            )
                        
                        validated_count += 1
                except ValueError:
                    errors.append(f"{req.product.name}: Quantité invalide")
        
        if errors:
            for error in errors:
                messages.warning(request, error)
        
        if validated_count > 0:
            messages.success(request, f"{validated_count} demande(s) validée(s) avec succès.")
        elif not errors:
            messages.info(request, "Aucune demande validée.")
        
        return redirect(request.path + f"?date={selected_date.strftime('%Y-%m-%d')}")
    
    # Prepare request data with stock info
    request_data = []
    for req in requests:
        available = warehouse_stock.get(req.product, Decimal('0'))
        request_data.append({
            'request': req,
            'available_stock': available,
            'can_approve_full': available >= req.requested_quantity,
        })
    
    return render(request, "mobile_pos/validate_inventory_requests.html", {
        "request_data": request_data,
        "selected_date": selected_date.strftime('%Y-%m-%d'),
        "warehouse": warehouse,
    })
