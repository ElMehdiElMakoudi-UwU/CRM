from django.urls import path
from . import views

app_name = 'clients'

urlpatterns = [
    # Clients
    path('', views.ClientListView.as_view(), name='client_list'),
    path('create/', views.ClientCreateView.as_view(), name='client_create'),
    path('<int:pk>/', views.ClientDetailView.as_view(), name='client_detail'),
    path('<int:pk>/update/', views.ClientUpdateView.as_view(), name='client_update'),
    path('<int:pk>/delete/', views.ClientDeleteView.as_view(), name='client_delete'),
    path('export/excel/', views.client_export_excel, name='client_export_excel'),
    path('export/pdf/', views.client_export_pdf, name='client_export_pdf'),



    # Segments
    path('segments/', views.SegmentListView.as_view(), name='segment_list'),
    path('segments/create/', views.SegmentCreateView.as_view(), name='segment_create'),
    path('segments/<int:pk>/update/', views.SegmentUpdateView.as_view(), name='segment_update'),
    path('segments/<int:pk>/delete/', views.SegmentDeleteView.as_view(), name='segment_delete'),
]
