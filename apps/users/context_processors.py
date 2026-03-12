from django.conf import settings


def demo_context(request):
    return {
        'show_demo_login_hint': settings.SHOW_DEMO_LOGIN_HINT,
    }
