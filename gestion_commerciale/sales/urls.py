from django.urls import path
from . import views
from . import api

app_name = 'sales'

urlpatterns = [
    path('', views.sale_list, name='sale_list'),
    path('create/', views.sale_create, name='sale_create'),
    path('<int:pk>/', views.sale_detail, name='sale_detail'),
    path('get_product_price/', views.get_product_price, name='get_product_price'),
    path('create_client/', views.create_client_ajax, name='create_client_ajax'),
    path('search_products/', views.search_products, name='search_products'),
    path('<int:pk>/facture/', views.sale_invoice_pdf, name='sale_invoice_pdf'),
    path('monthly/', views.monthly_sales, name='monthly_sales'),
    path('monthly/pdf/', views.generate_monthly_invoices_pdf, name='generate_monthly_invoices_pdf'),
]
