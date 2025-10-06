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
    
    # URLs de réinitialisation de mot de passe
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    
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
    path('mobile-pos/', include('mobile_pos.urls')),
    path('comptabilite/', include('comptabilite.urls')),
    path('pricing/', include('pricing.urls')),
    path('sellers/', include('sellers.urls')),
    path('operations/', include('operations.urls')),
]