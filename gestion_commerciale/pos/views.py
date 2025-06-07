from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.shortcuts import get_object_or_404
from products.models import Product
from .models import POSReceipt, POSLineItem
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from django.shortcuts import render
from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField, Value, Subquery, OuterRef
from django.db.models.functions import Coalesce, Cast
from datetime import datetime, time
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@login_required
def pos_main_view(request):
    return render(request, 'pos/pos_interface.html')

@require_GET
@login_required
def product_list_view(request):
    products = Product.objects.all()
    data = [
        {
            "id": p.id,
            "name": p.name,
            "price": float(p.selling_price),
            "image_url": p.image.url if p.image else "/static/images/default-product.png"
        }
        for p in products
    ]
    return JsonResponse(data, safe=False)


@require_GET
@login_required
def product_search_view(request):
    query = request.GET.get("q", "")
    products = Product.objects.filter(name__icontains=query)[:10]
    data = [
        {
            "id": p.id,
            "name": p.name,
            "price": float(p.selling_price),
            "image_url": p.image.url if p.image else "/static/images/default-product.png"
        }
        for p in products
    ]
    return JsonResponse(data, safe=False)


from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from django.db import transaction
from products.models import Product
from inventory.models import Stock
from .models import POSReceipt, POSLineItem

@require_POST
@login_required
@transaction.atomic
def checkout_view(request):
    paid = Decimal(request.POST.get("paid", "0"))
    total = Decimal(request.POST.get("total", "0"))
    method = request.POST.get("method")
    items = request.POST.getlist("items[]")

    receipt = POSReceipt.objects.create(
        cashier=request.user,
        total=total,
        paid=paid,
        payment_method=method,
    )

    for item_str in items:
        try:
            product_id, qty_str, unit_price_str = item_str.split(",")
            qty = Decimal(qty_str)
            unit_price = Decimal(unit_price_str)

            product = Product.objects.get(id=int(product_id))

            # ✅ Récupération du stock lié au produit et à son entrepôt par défaut
            stock_entry = Stock.objects.select_for_update().get(
                product=product,
                warehouse=product.default_warehouse
            )

            if stock_entry.quantity < qty:
                return JsonResponse({
                    "status": "error",
                    "message": f"Stock insuffisant pour {product.name} (disponible : {stock_entry.quantity})"
                })

            # 💾 Création de la ligne de vente
            POSLineItem.objects.create(
                receipt=receipt,
                product=product,
                quantity=int(qty),
                unit_price=unit_price
            )

            # 📉 Décrémentation du stock
            stock_entry.quantity -= qty
            stock_entry.save()

        except Stock.DoesNotExist:
            return JsonResponse({
                "status": "error",
                "message": f"Aucun stock trouvé pour {product.name} dans l'entrepôt par défaut."
            })
        except Exception as e:
            print(f"Erreur produit {item_str} -> {e}")
            continue

    return JsonResponse({"status": "ok", "receipt_id": receipt.id})
    

from django.shortcuts import render, get_object_or_404
from .models import POSReceipt, POSLineItem

@login_required
def receipt_print_view(request, receipt_id):
    receipt = get_object_or_404(POSReceipt, id=receipt_id)
    items = POSLineItem.objects.filter(receipt=receipt)

    subtotal = sum(item.unit_price * item.quantity for item in items)
    vat = subtotal * Decimal('0.2')
    total = subtotal + vat
    change = receipt.paid - total
    context = {
        'receipt': receipt,
        'items': items,
        'subtotal': subtotal,
        'vat': vat,
        'total': total,
        'change': change,
    }
    return render(request, 'pos/receipt_print.html', context)

@login_required
def daily_recap_view(request):
    # Payment method display names mapping
    PAYMENT_METHODS = {
        'cash': 'Espèces',
        'card': 'Carte',
        'credit': 'Crédit'
    }
    
    # Get today's date range
    today = timezone.now().date()
    today_start = timezone.make_aware(datetime.combine(today, time.min))
    today_end = timezone.make_aware(datetime.combine(today, time.max))
    
    # Get all receipts for today
    receipts = POSReceipt.objects.filter(created_at__range=(today_start, today_end))
    
    # Calculate total sales and transaction count
    total_sales = receipts.aggregate(
        total=Coalesce(Sum('total'), Decimal('0'))
    )['total']
    
    transaction_count = receipts.count()
    average_sale = Decimal('0') if transaction_count == 0 else total_sales / transaction_count
    
    # Get payment method statistics
    payment_methods = []
    for method_stats in receipts.values('payment_method').annotate(
        count=Count('id'),
        total=Sum('total')
    ).order_by('-total'):
        method_stats['method'] = PAYMENT_METHODS.get(method_stats['payment_method'], method_stats['payment_method'])
        payment_methods.append(method_stats)
    
    # Debug: Check if we have any receipts
    logger.debug(f"Found {receipts.count()} receipts for today")
    
    # Get all line items first to check
    all_line_items = POSLineItem.objects.filter(receipt__in=receipts)
    logger.debug(f"Found {all_line_items.count()} line items")
    
    # Get top selling products with raw aggregation
    top_products_raw = POSLineItem.objects.filter(
        receipt__in=receipts
    ).values(
        'product__name'
    ).annotate(
        name=F('product__name'),
        quantity=Sum('quantity')
    ).values(
        'name',
        'quantity'
    ).order_by('-quantity')[:10]
    
    # Convert to list and calculate totals
    top_products = []
    for product in top_products_raw:
        # Get all line items for this product
        product_items = all_line_items.filter(product__name=product['name'])
        total = sum(item.quantity * item.unit_price for item in product_items)
        top_products.append({
            'name': product['name'],
            'quantity': product['quantity'],
            'total': total
        })
    
    # Sort by total
    top_products.sort(key=lambda x: x['total'], reverse=True)
    
    context = {
        'date': today,
        'total_sales': total_sales,
        'transaction_count': transaction_count,
        'average_sale': average_sale,
        'payment_methods': payment_methods,
        'top_products': top_products,
    }
    
    return render(request, 'pos/daily_recap.html', context)
