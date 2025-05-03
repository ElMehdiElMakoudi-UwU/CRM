from django.urls import path
from . import views
from . import api

app_name = 'sales'

urlpatterns = [
    path('', views.sale_list, name='sale_list'),
    path('new/', views.sale_create, name='sale_create'),
    path('<int:pk>/', views.sale_detail, name='sale_detail'),
    path('get-price/<int:product_id>/', api.get_product_price, name='get_product_price'),
]
