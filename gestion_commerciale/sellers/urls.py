from django.urls import path
from . import views

app_name = 'sellers'

urlpatterns = [
    path('load-inventory/', views.load_inventory, name='load_inventory'),
    path('unload-inventory/', views.unload_inventory, name='unload_inventory'),
] 