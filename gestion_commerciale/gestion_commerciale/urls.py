from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from . import views


urlpatterns = [
    path('', views.dashboard_view, name='home'),
    path('admin/', admin.site.urls),
    # path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('users/', include('users.urls'), name='users'),
    path('products/', include('products.urls')),
    path('suppliers/', include('suppliers.urls')),
    path('inventory/', include('inventory.urls')),
    path('clients/', include('clients.urls')),
    path('sales/', include('sales.urls')),
    path('pos/', include('pos.urls')),
    path("payments/", include("payments.urls")),
    path("purchases/", include("purchases.urls")),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),

]