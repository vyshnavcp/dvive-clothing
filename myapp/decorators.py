from django.core.exceptions import PermissionDenied
from functools import wraps
from django.shortcuts import redirect

def role_required(allowed_roles=None):

    if allowed_roles is None:
        allowed_roles=[]

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request,*args,**kwargs):

            if not request.user.is_authenticated:
                return redirect("user_login")

            if request.user.is_superuser:
                return view_func(request,*args,**kwargs)

            user_groups=request.user.groups.values_list('name',flat=True)

            if any(role in user_groups for role in allowed_roles):
                return view_func(request,*args,**kwargs)

            raise PermissionDenied

        return wrapper

    return decorator