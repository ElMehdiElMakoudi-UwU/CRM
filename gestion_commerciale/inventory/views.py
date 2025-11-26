from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from products.models import Product
from .models import Stock, StockMovement, StockAlert, Warehouse
from .forms import StockMovementForm, StockForm, WarehouseForm
from django.utils import timezone
from django.db.models import Sum, F, Q
from itertools import groupby
from operator import attrgetter

@login_required
def stock_list_view(request):
    warehouse_id = request.GET.get('warehouse')
    category_id = request.GET.get('category')
    search = request.GET.get('search', '').strip()

    # Base queryset
    stocks = Stock.objects.select_related('product', 'warehouse').all()

    # Apply filters
    if warehouse_id:
        stocks = stocks.filter(warehouse_id=warehouse_id)
    if category_id:
        stocks = stocks.filter(product__category_id=category_id)
    if search:
        stocks = stocks.filter(
            Q(product__name__icontains=search) |
            Q(product__reference__icontains=search)
        )

    # Get all warehouses for the filter dropdown
    warehouses = Warehouse.objects.all()
    
    # Get all categories for the filter dropdown - handle if category doesn't exist
    try:
        categories = Product.objects.values('category__id', 'category__name').distinct()
    except:
        categories = []

    # Group stocks by product
    stocks = stocks.order_by('product__name', 'warehouse__name')
    grouped_stocks = {}
    
    for stock in stocks:
        if stock.product_id not in grouped_stocks:
            grouped_stocks[stock.product_id] = {
                'product': stock.product,
                'warehouses': {},
                'total_quantity': 0,
                'total_threshold': stock.product.reorder_threshold,
                'any_below_threshold': False
            }
        
        grouped_stocks[stock.product_id]['warehouses'][stock.warehouse_id] = {
            'warehouse': stock.warehouse,
            'quantity': stock.quantity,
            'threshold': stock.product.reorder_threshold,
            'is_below_threshold': stock.quantity <= stock.product.reorder_threshold
        }
        
        grouped_stocks[stock.product_id]['total_quantity'] += stock.quantity
        if stock.quantity <= stock.product.reorder_threshold:
            grouped_stocks[stock.product_id]['any_below_threshold'] = True

    context = {
        'grouped_stocks': grouped_stocks,
        'warehouses': warehouses,
        'categories': categories,
        'filters': {
            'warehouse': warehouse_id,
            'category': category_id,
            'search': search
        }
    }
    return render(request, 'inventory/stock_list.html', context)

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import StockMovement, Product, Warehouse
from datetime import datetime

@login_required
def stock_movement_list_view(request):
    movements = StockMovement.objects.select_related('product', 'warehouse', 'user', 'from_warehouse', 'to_warehouse').order_by('-date')

    # Filtres
    product_id = request.GET.get('product')
    warehouse_id = request.GET.get('warehouse')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if product_id:
        movements = movements.filter(product_id=product_id)

    if warehouse_id:
        movements = movements.filter(Q(warehouse_id=warehouse_id) | Q(from_warehouse_id=warehouse_id) | Q(to_warehouse_id=warehouse_id))

    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            movements = movements.filter(date__gte=start)
        except:
            pass

    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d")
            movements = movements.filter(date__lte=end)
        except:
            pass

    context = {
        'movements': movements,
        'products': Product.objects.all(),
        'warehouses': Warehouse.objects.all(),
        'filter_values': {
            'product': product_id,
            'warehouse': warehouse_id,
            'start_date': start_date,
            'end_date': end_date
        }
    }
    return render(request, 'inventory/stock_movement_list.html', context)

@login_required
def stock_movement_create_view(request):
    if request.method == 'POST':
        form = StockMovementForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.user = request.user
            movement.date = timezone.now()
            movement.save()
            messages.success(request, "Mouvement de stock enregistré.")
            return redirect('stock_movement_list')
    else:
        form = StockMovementForm()

    return render(request, 'inventory/stock_movement_form.html', {'form': form})

@login_required
def stock_alerts_view(request):
    alerts = StockAlert.objects.select_related('product', 'warehouse').filter(is_resolved=False).order_by('-created_at')
    return render(request, 'inventory/stock_alerts.html', {'alerts': alerts})

@login_required
def warehouse_list_view(request):
    warehouses = Warehouse.objects.all()
    return render(request, 'inventory/warehouse_list.html', {'warehouses': warehouses})

@login_required
def warehouse_create_view(request):
    if request.method == 'POST':
        form = WarehouseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Entrepôt créé avec succès.")
            return redirect('inventory:warehouse_list')
    else:
        form = WarehouseForm()
    
    return render(request, 'inventory/warehouse_form.html', {'form': form})

@login_required
def warehouse_inventory_summary_view(request, warehouse_id):
    warehouse = get_object_or_404(Warehouse, id=warehouse_id)
    stocks = Stock.objects.filter(warehouse=warehouse)
    total_quantity = stocks.aggregate(total=Sum('quantity'))['total']
    return render(request, 'inventory/warehouse_summary.html', {
        'warehouse': warehouse,
        'stocks': stocks,
        'total_quantity': total_quantity,
    })

@login_required
def stock_create_or_update_view(request):
    if request.method == 'POST':
        form = StockForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Stock enregistré/ajusté.")
            return redirect('inventory:stock_list')
    else:
        form = StockForm()

    return render(request, 'inventory/stock_form.html', {'form': form})


from .forms import StockTransferForm

@login_required
def stock_transfer_view(request):
    if request.method == 'POST':
        form = StockTransferForm(request.POST)
        if form.is_valid():
            transfer = form.save(commit=False)
            transfer.movement_type = 'transfer'
            transfer.user = request.user
            transfer.date = timezone.now()
            
            # Vérifier si le stock est suffisant avant le transfert
            from_stock = Stock.objects.filter(
                product=transfer.product,
                warehouse=transfer.from_warehouse
            ).first()
            
            if not from_stock or from_stock.quantity < transfer.quantity:
                messages.error(request, f"Stock insuffisant dans {transfer.from_warehouse.name}.")
                return redirect('inventory:stock_transfer')
                
            transfer.save()
            messages.success(request, "Transfert effectué avec succès.")
            return redirect('inventory:stock_movement_list')
    else:
        form = StockTransferForm()

    return render(request, 'inventory/stock_transfer_form.html', {'form': form})
