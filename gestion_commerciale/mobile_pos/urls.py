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
    path('sw.js', views.serve_service_worker, name='sw.js'),
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('analytics/products/', views.product_performance, name='product_performance'),
    path('analytics/sales-reps/', views.sales_rep_analytics, name='sales_rep_analytics'),
] 