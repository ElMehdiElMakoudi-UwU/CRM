# users/decorators.py

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

def role_required(*allowed_roles):
    def decorator(view_func):
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.userprofile.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            return redirect('no-permission')
        return wrapper
    return decorator
