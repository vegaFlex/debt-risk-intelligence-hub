from functools import wraps

from django.shortcuts import render


def _access_denied_response(request, *, message, required_role, primary_action=None):
    return render(
        request,
        'access_denied.html',
        {
            'message': message,
            'required_role': required_role,
            'primary_action': primary_action
            or {
                'label': 'Back to Home',
                'url': '/',
                'style': 'btn-secondary',
            },
        },
        status=200,
    )


def manager_or_admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return view_func(request, *args, **kwargs)

        if getattr(user, 'role', None) not in {'manager', 'admin'}:
            primary_action = {
                'label': 'Open Debtor API',
                'url': '/api/debtors/',
                'style': 'btn-secondary',
            }
            if getattr(user, 'role', None) == 'visitor':
                primary_action = {
                    'label': 'Open Valuation Workspace',
                    'url': '/valuation/',
                    'style': 'btn-secondary',
                }
            elif getattr(user, 'role', None) not in {'analyst'}:
                primary_action = {
                    'label': 'Back to Home',
                    'url': '/',
                    'style': 'btn-secondary',
                }

            message = 'You do not have permission to access this page.'
            if getattr(user, 'role', None) == 'visitor':
                message = 'This demo account is view-only. Sign in with a manager or admin account to make changes.'

            return _access_denied_response(
                request,
                message=message,
                required_role='Manager or Admin',
                primary_action=primary_action,
            )

        return view_func(request, *args, **kwargs)

    return _wrapped


def viewer_or_manager_or_admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return view_func(request, *args, **kwargs)

        if getattr(user, 'role', None) not in {'visitor', 'manager', 'admin'}:
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
            return _access_denied_response(
                request,
                message='You do not have permission to access this page.',
                required_role='Visitor, Manager or Admin',
                primary_action=primary_action,
            )

        return view_func(request, *args, **kwargs)

    return _wrapped
