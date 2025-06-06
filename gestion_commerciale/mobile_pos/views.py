from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Order, OrderItem
from products.models import Product

# Create your views here.

@login_required
def order_list(request):
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'mobile_pos/order_list.html', {'orders': orders})

@login_required
def create_order(request):
    products = Product.objects.all()
    if request.method == 'POST':
        client_name = request.POST.get('client_name')
        client_contact = request.POST.get('client_contact')
        notes = request.POST.get('notes')
        
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
    
    return render(request, 'mobile_pos/create_order.html', {'products': products})

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
