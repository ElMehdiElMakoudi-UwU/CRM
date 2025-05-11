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


@require_POST
@login_required
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
            product_id, qty, unit_price = item_str.split(",")
            POSLineItem.objects.create(
                receipt=receipt,
                product_id=int(product_id),
                quantity=int(qty),
                unit_price=Decimal(unit_price)
            )
        except Exception as e:
            print(f"Error saving item: {item_str} -> {e}")
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
