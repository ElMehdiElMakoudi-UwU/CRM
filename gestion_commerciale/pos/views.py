from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.shortcuts import get_object_or_404
from products.models import Product
from .models import POSReceipt, POSLineItem
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from django.shortcuts import render

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
