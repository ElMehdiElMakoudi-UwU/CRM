from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from django.shortcuts import render

# Import tes modèles si tu veux des données réelles
# from sales.models import Sale
# from products.models import Product
# from clients.models import Client

@login_required
def dashboard_view(request):
    context = {
        "now": now(),
        # 🔽 Exemples de données dynamiques à intégrer plus tard :
        # "total_sales_today": Sale.objects.filter(date=now().date()).aggregate(Sum('total'))["total__sum"] or 0,
        # "products_in_stock": Product.objects.count(),
        # "clients_total": Client.objects.count(),
    }
    return render(request, "dashboard/dashboard.html", context)
