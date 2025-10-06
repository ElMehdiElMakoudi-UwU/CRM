from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Supplier, PurchaseOrder
from .forms import SupplierForm, PurchaseOrderForm, PurchaseOrderItemFormSet

# ------------------------
# Gestion des Fournisseurs
# ------------------------

from django.shortcuts import render
from .models import Supplier
from django.db.models import Q

def supplier_list(request):
    search_query = request.GET.get('search', '')
    suppliers = Supplier.objects.all()

    if search_query:
        suppliers = suppliers.filter(
            Q(name__icontains=search_query) | Q(email__icontains=search_query)
        )

    if request.htmx:
        return render(request, 'supplier/partials/supplier_rows.html', {'suppliers': suppliers})

    return render(request, 'supplier/supplier_list.html', {'suppliers': suppliers})

def supplier_create(request):
    form = SupplierForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Fournisseur ajouté avec succès.")
        return redirect('suppliers:supplier_list')
    return render(request, 'supplier/supplier_form.html', {'form': form})

def supplier_update(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    form = SupplierForm(request.POST or None, instance=supplier)
    if form.is_valid():
        form.save()
        messages.success(request, "Fournisseur mis à jour.")
        return redirect('suppliers:supplier_list')
    return render(request, 'supplier/supplier_form.html', {'form': form})

def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == "POST":
        supplier.delete()
        messages.success(request, "Fournisseur supprimé.")
        return redirect('suppliers:supplier_list')
    return render(request, 'supplier/supplier_confirm_delete.html', {'supplier': supplier})

# ------------------------
# Gestion des Commandes
# ------------------------

def purchase_order_list(request):
    orders = PurchaseOrder.objects.select_related('supplier').all()
    return render(request, 'supplier/purchase_order_list.html', {'orders': orders})

def purchase_order_create(request):
    form = PurchaseOrderForm(request.POST or None)
    formset = PurchaseOrderItemFormSet(request.POST or None)
    if form.is_valid() and formset.is_valid():
        order = form.save()
        items = formset.save(commit=False)
        for item in items:
            item.order = order
            item.save()
        messages.success(request, "Commande fournisseur créée.")
        return redirect('suppliers:purchase_order_list')
    return render(request, 'supplier/purchase_order_form.html', {
        'form': form,
        'formset': formset
    })

def purchase_order_detail(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    return render(request, 'supplier/purchase_order_detail.html', {'order': order})
