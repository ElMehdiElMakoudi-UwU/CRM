from django.urls import path
from . import views

app_name = 'purchases'

urlpatterns = [
    path("", views.purchase_list, name="purchase_list"),
    path("new/", views.purchase_create, name="purchase_create"),
    path("<int:pk>/", views.purchase_detail, name="purchase_detail"),
    path("<int:purchase_id>/add-payment/", views.add_supplier_payment, name="add_supplier_payment"),
    path("product-selector/", views.product_selector, name="product_selector"),
    path("purchase/<int:pk>/bon-de-commande/", views.purchase_order_pdf, name="purchase_order_pdf"),
    path("<int:pk>/receive/", views.receive_purchase, name="receive_purchase"),
]
