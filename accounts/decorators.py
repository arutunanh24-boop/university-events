from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if request.user.is_coursework_admin or request.user.role in roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, 'У вас нет прав для выполнения этого действия.')
            return redirect('events:event_list')

        return wrapper

    return decorator


def organizer_or_admin_required(view_func):
    return role_required('organizer', 'admin')(view_func)


def admin_required(view_func):
    return role_required('admin')(view_func)
