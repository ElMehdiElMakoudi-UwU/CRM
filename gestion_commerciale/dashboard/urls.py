from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),

    # Sous-sections par domaine
    path('sales/', views.sales_dashboard_view, name='sales'),
    path('stock/', views.stock_dashboard_view, name='stock'),
    path('pos/', views.pos_dashboard_view, name='pos'),
    path('clients/', views.clients_dashboard_view, name='clients'),
    path('purchases/', views.purchases_dashboard_view, name='purchases'),
]
