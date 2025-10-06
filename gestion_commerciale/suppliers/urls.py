from django.urls import path
from . import views

app_name = 'suppliers'


urlpatterns = [
    # Fournisseurs
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/add/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/edit/', views.supplier_update, name='supplier_update'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),

    # Commandes fournisseurs
    path('orders/', views.purchase_order_list, name='purchase_order_list'),
    path('orders/add/', views.purchase_order_create, name='purchase_order_create'),
    path('orders/<int:pk>/', views.purchase_order_detail, name='purchase_order_detail'),
]
