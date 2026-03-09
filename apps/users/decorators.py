from functools import wraps

from django.core.exceptions import PermissionDenied


def manager_or_admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated or getattr(user, 'role', None) not in {'manager', 'admin'}:
            raise PermissionDenied('Manager or Admin role required.')
        return view_func(request, *args, **kwargs)

    return _wrapped
