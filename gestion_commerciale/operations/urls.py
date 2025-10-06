from django.urls import path
from . import views

app_name = 'operations'

urlpatterns = [
    # Path for loading inventory onto the vehicle
    path('load/', views.load_new_inventory, name='load_inventory'),
    
    # Path for unloading inventory and calculating sales
    path('unload/', views.unload_new_inventory, name='unload_inventory'),
    
    # Path for exporting the unload report as PDF
    path('unload/pdf/<int:seller_id>/<str:date_str>/', 
         views.export_unload_pdf, name='export_unload_pdf'),
]
