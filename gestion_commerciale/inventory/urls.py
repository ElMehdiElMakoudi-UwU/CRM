from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('stocks/', views.stock_list_view, name='stock_list'),
    path('stocks/new/', views.stock_create_or_update_view, name='stock_create_or_update'),
    path('movements/', views.stock_movement_list_view, name='stock_movement_list'),
    path('movements/new/', views.stock_movement_create_view, name='stock_movement_create'),
    path('alerts/', views.stock_alerts_view, name='stock_alerts'),
    path('warehouses/', views.warehouse_list_view, name='warehouse_list'),
    path('warehouses/<int:warehouse_id>/summary/', views.warehouse_inventory_summary_view, name='warehouse_summary'),
    path('transfers/', views.stock_transfer_view, name='stock_transfer'),

]
