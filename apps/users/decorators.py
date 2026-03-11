from functools import wraps

from django.shortcuts import render


def manager_or_admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            # login_required decorator should handle this case upstream.
            return view_func(request, *args, **kwargs)

        if getattr(user, 'role', None) not in {'manager', 'admin'}:
            primary_action = {
                'label': 'Open Debtor API',
                'url': '/api/debtors/',
                'style': 'btn-secondary',
            }
            if getattr(user, 'role', None) not in {'analyst'}:
                primary_action = {
                    'label': 'Back to Home',
                    'url': '/',
                    'style': 'btn-secondary',
                }

            return render(
                request,
                'access_denied.html',
                {
                    'message': 'You do not have permission to access this page.',
                    'required_role': 'Manager or Admin',
                    'primary_action': primary_action,
                },
                status=200,
            )

        return view_func(request, *args, **kwargs)

    return _wrapped
