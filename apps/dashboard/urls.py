from django.urls import path

from apps.dashboard.views import debtor_results_view, management_dashboard_view


urlpatterns = [
    path('', management_dashboard_view, name='dashboard-home'),
    path('debtors/', debtor_results_view, name='dashboard-debtor-results'),
]
