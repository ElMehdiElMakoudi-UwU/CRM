# users/decorators.py

from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def role_required(allowed_roles=[]):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.profile.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "Vous n'avez pas la permission d'accéder à cette page.")
                if request.user.profile.role == 'sales_rep':
                    return redirect('mobile_pos:create_order')
                return redirect('dashboard')
        return wrapper
    return decorator
