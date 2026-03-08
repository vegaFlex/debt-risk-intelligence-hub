from django.urls import path

from apps.dashboard.views import management_dashboard_view


urlpatterns = [
    path('', management_dashboard_view, name='dashboard-home'),
]
