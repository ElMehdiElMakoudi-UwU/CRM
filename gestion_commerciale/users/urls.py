from django.urls import path
from . import views
from django.shortcuts import render

app_name = 'users'


urlpatterns = [
    path('', views.user_list, name='user_list'),
    path('add/', views.user_create, name='user_create'),
    path('edit/<int:pk>/', views.user_edit, name='user_edit'),
    path('profile/', views.user_profile, name='profile'),
    path('no-permission/', lambda r: render(r, 'users/no_permission.html'), name='no-permission'),
]
