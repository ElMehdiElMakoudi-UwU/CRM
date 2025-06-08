from django.urls import path
from . import views

app_name = 'purchases'

urlpatterns = [
    path('', views.purchase_list_view, name='purchase_list'),
    path('new/', views.purchase_create, name='purchase_create'),
    path('<int:pk>/', views.purchase_detail, name='purchase_detail'),
    path('<int:pk>/receive/', views.receive_purchase, name='receive_purchase'),
    path('<int:purchase_id>/payment/', views.add_supplier_payment, name='add_supplier_payment'),
    path('<int:pk>/pdf/', views.purchase_order_pdf, name='purchase_order_pdf'),
    path('monthly/', views.monthly_purchases, name='monthly_purchases'),
    path('monthly/pdf/', views.generate_monthly_invoices_pdf, name='generate_monthly_invoices_pdf'),
    path('product-selector/', views.product_selector, name='product_selector'),
]
