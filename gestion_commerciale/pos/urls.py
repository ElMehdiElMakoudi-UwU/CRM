from django.urls import path
from . import views

app_name = 'pos'

urlpatterns = [
    path('', views.pos_main_view, name='interface'),
    path('products/', views.product_list_view, name='product_list'),
    path('search/', views.product_search_view, name='product_search'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('receipt/<int:receipt_id>/', views.receipt_print_view, name='receipt_print'),
    path('daily-recap/', views.daily_recap_view, name='daily_recap'),
]
