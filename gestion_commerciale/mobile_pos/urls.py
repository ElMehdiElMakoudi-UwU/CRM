from django.urls import path
from . import views

app_name = 'mobile_pos'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('orders/', views.order_list, name='order_list'),
    path('create/', views.create_order, name='create_order'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('order/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('client/<int:client_id>/history/', views.client_history, name='client_history'),
    path('offline/', views.offline_page, name='offline'),
    path('api/sync-order/', views.sync_order, name='sync_order'),
    path('api/products/', views.api_products, name='api_products'),
    path('api/product-by-barcode/', views.api_product_by_barcode, name='api_product_by_barcode'),
    path('api/search-clients/', views.api_search_clients, name='api_search_clients'),
    path('sw.js', views.serve_service_worker, name='sw.js'),
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('analytics/products/', views.product_performance, name='product_performance'),
    path('analytics/sales-reps/', views.sales_rep_analytics, name='sales_rep_analytics'),
    # Inventory Requests
    path('inventory-requests/', views.inventory_request_list, name='inventory_request_list'),
    path('inventory-requests/create/', views.inventory_request_create, name='inventory_request_create'),
    path('inventory-requests/<int:request_id>/', views.inventory_request_detail, name='inventory_request_detail'),
    # Client Management (Mobile)
    path('clients/', views.client_list_mobile, name='client_list_mobile'),
    path('clients/create/', views.client_create_mobile, name='client_create_mobile'),
    path('clients/outstanding-debt/', views.client_outstanding_debt, name='client_outstanding_debt'),
    path('api/create-client/', views.api_create_client, name='api_create_client'),
    # Sales (Mobile)
    path('sales/', views.sale_list_mobile, name='sale_list_mobile'),
    path('sales/create/', views.sale_create_mobile, name='sale_create_mobile'),
    path('sales/<int:sale_id>/', views.sale_detail_mobile, name='sale_detail_mobile'),
    # Inventory Load/Unload (Mobile)
    path('inventory/load/', views.mobile_load_inventory, name='mobile_load_inventory'),
    path('inventory/status/', views.mobile_inventory_status, name='mobile_inventory_status'),
    path('inventory/validate/', views.validate_inventory_requests, name='validate_inventory_requests'),
    # Manager-only: Log unloads for sales reps
    path('inventory/log-unload/', views.manager_log_unload, name='manager_log_unload'),
] 