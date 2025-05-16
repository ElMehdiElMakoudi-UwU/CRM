from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from products.models import Product
from .models import Stock, StockMovement, StockAlert, Warehouse
from .forms import StockMovementForm, StockForm
from django.utils import timezone
from django.db.models import Sum

@login_required
def stock_list_view(request):
    warehouse_id = request.GET.get('warehouse')
    if warehouse_id:
        stocks = Stock.objects.select_related('product', 'warehouse').filter(warehouse_id=warehouse_id)
    else:
        stocks = Stock.objects.select_related('product', 'warehouse').all()
    warehouses = Warehouse.objects.all()
    return render(request, 'inventory/stock_list.html', {'stocks': stocks, 'warehouses': warehouses})

@login_required
def stock_movement_list_view(request):
    movements = StockMovement.objects.select_related('product', 'warehouse', 'user').order_by('-date')
    return render(request, 'inventory/stock_movement_list.html', {'movements': movements})

@login_required
def stock_movement_create_view(request):
    if request.method == 'POST':
        form = StockMovementForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.user = request.user
            movement.date = timezone.now()
            movement.save()

            # Mise à jour du stock
            stock, created = Stock.objects.get_or_create(
                product=movement.product,
                warehouse=movement.warehouse,
                defaults={'quantity': 0}
            )
            if movement.movement_type == 'in':
                stock.quantity += movement.quantity
            elif movement.movement_type == 'out':
                stock.quantity -= movement.quantity
            elif movement.movement_type == 'adjustment':
                stock.quantity = movement.quantity
            elif movement.movement_type == 'transfer':
                # Sortie de from_warehouse
                from_stock, _ = Stock.objects.get_or_create(
                    product=movement.product,
                    warehouse=movement.from_warehouse,
                    defaults={'quantity': 0}
                )
                to_stock, _ = Stock.objects.get_or_create(
                    product=movement.product,
                    warehouse=movement.to_warehouse,
                    defaults={'quantity': 0}
                )
                from_stock.quantity -= movement.quantity
                to_stock.quantity += movement.quantity
                from_stock.save()
                to_stock.save()
                messages.success(request, "Transfert entre dépôts enregistré.")
                return redirect('stock_movement_list')

            stock.save()
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
            transfer.save()

            from_stock, _ = Stock.objects.get_or_create(
                product=transfer.product,
                warehouse=transfer.from_warehouse,
                defaults={'quantity': 0}
            )
            to_stock, _ = Stock.objects.get_or_create(
                product=transfer.product,
                warehouse=transfer.to_warehouse,
                defaults={'quantity': 0}
            )

            if from_stock.quantity < transfer.quantity:
                messages.error(request, f"Stock insuffisant dans {from_stock.warehouse.name}.")
                return redirect('inventory:stock_transfer')

            from_stock.quantity -= transfer.quantity
            to_stock.quantity += transfer.quantity
            from_stock.save()
            to_stock.save()

            messages.success(request, "Transfert effectué avec succès.")
            return redirect('inventory:stock_movement_list')
    else:
        form = StockTransferForm()

    return render(request, 'inventory/stock_transfer_form.html', {'form': form})
