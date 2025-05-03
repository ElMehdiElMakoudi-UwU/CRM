from django.urls import path
from . import views

app_name = 'inventory'


urlpatterns = [
    path('stocks/', views.stock_list_view, name='stock_list'),
    path('movements/', views.stock_movement_list_view, name='stock_movement_list'),
    path('movements/new/', views.stock_movement_create_view, name='stock_movement_create'),
    path('alerts/', views.stock_alerts_view, name='stock_alerts'),
]
