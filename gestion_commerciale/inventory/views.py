from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from products.models import Product
from .models import Stock, StockMovement, StockAlert
from .forms import StockMovementForm
from django.utils import timezone

@login_required
def stock_list_view(request):
    stocks = Stock.objects.select_related('product').all()
    return render(request, 'inventory/stock_list.html', {'stocks': stocks})


@login_required
def stock_movement_list_view(request):
    movements = StockMovement.objects.select_related('product', 'user').order_by('-date')
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
            stock = Stock.objects.get(product=movement.product)
            if movement.movement_type == 'in':
                stock.quantity += movement.quantity
            elif movement.movement_type == 'out':
                stock.quantity -= movement.quantity
            elif movement.movement_type == 'adjustment':
                stock.quantity = movement.quantity
            stock.save()

            messages.success(request, "Mouvement de stock enregistré.")
            return redirect('stock_movement_list')
    else:
        form = StockMovementForm()

    return render(request, 'inventory/stock_movement_form.html', {'form': form})


@login_required
def stock_alerts_view(request):
    alerts = StockAlert.objects.select_related('product').filter(is_resolved=False).order_by('-created_at')
    return render(request, 'inventory/stock_alerts.html', {'alerts': alerts})
