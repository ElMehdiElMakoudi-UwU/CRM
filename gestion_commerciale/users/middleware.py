from django.shortcuts import redirect
from django.urls import resolve, reverse
from django.conf import settings

class RoleBasedRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            current_url = resolve(request.path_info).url_name
            
            # Skip middleware for static files, admin, and API endpoints
            if any([
                request.path.startswith('/static/'),
                request.path.startswith('/admin/'),
                request.path.startswith('/api/'),
                request.path.startswith('/media/'),
                request.path.startswith('/mobile-pos/'),  # Allow all mobile-pos URLs
                'login' in current_url,
                'logout' in current_url,
            ]):
                return self.get_response(request)

            # Get user role
            user_role = request.user.profile.role

            # Define allowed URLs for each role
            role_urls = {
                'sales_rep': [
                    'mobile_pos',
                    'dashboard',
                    'create_order',
                    'order_detail',
                    'order_list',
                    'client_history',
                    'offline',
                    'sync_order',
                    'sw.js',
                    # Inventory management
                    'mobile_inventory_status',
                    'mobile_load_inventory',
                    'inventory_request_list',
                    'inventory_request_create',
                    'inventory_request_detail',
                    # Client management
                    'client_list_mobile',
                    'client_create_mobile',
                    # Sales
                    'sale_list_mobile',
                    'sale_create_mobile',
                    'sale_detail_mobile',
                ],
                'admin': ['*'],  # Admin can access everything
                'manager': ['*'],  # Manager can access everything
                'accountant': [
                    'dashboard',
                    'reports',
                    'sales_list',
                    'purchases_list',
                    'invoices',
                ],
            }

            # Get allowed URLs for user's role
            allowed_urls = role_urls.get(user_role, [])

            # If user is trying to access a non-allowed URL
            if '*' not in allowed_urls and current_url not in allowed_urls:
                # Redirect sales reps to mobile POS dashboard
                if user_role == 'sales_rep':
                    return redirect('mobile_pos:dashboard')
                # Add other role redirections here if needed

        return self.get_response(request) 