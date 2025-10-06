from django.urls import path
from . import views

app_name = 'pricing'

urlpatterns = [
    path('', views.price_grid_list, name='price_grid_list'),
    path('create/', views.price_grid_create, name='price_grid_create'),
    path('<int:pk>/', views.price_grid_detail, name='price_grid_detail'),
    path('<int:pk>/update/', views.price_grid_update, name='price_grid_update'),
    path('<int:grid_pk>/rules/create/', views.price_rule_create, name='price_rule_create'),
    path('rules/<int:pk>/update/', views.price_rule_update, name='price_rule_update'),
    path('rules/<int:pk>/delete/', views.price_rule_delete, name='price_rule_delete'),
] 