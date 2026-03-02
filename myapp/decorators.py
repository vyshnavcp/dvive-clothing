from django.core.exceptions import PermissionDenied
from functools import wraps

def role_required(allowed_roles=[]):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            if not request.user.is_authenticated:
                from django.shortcuts import redirect
                return redirect('user_login')

            # Allow Superuser always
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Allow Staff
            if "staff" in allowed_roles and request.user.is_staff:
                return view_func(request, *args, **kwargs)

            # If not allowed
            raise PermissionDenied

        return wrapper
    return decorator