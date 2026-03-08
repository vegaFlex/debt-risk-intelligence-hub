from django.urls import path

from apps.portfolio.api_views import (
    DebtorListAPIView,
    DebtorRiskDetailAPIView,
    KpiOverviewAPIView,
    PortfolioListAPIView,
)


urlpatterns = [
    path('portfolios/', PortfolioListAPIView.as_view(), name='api-portfolios-list'),
    path('debtors/', DebtorListAPIView.as_view(), name='api-debtors-list'),
    path('debtors/<int:pk>/score/', DebtorRiskDetailAPIView.as_view(), name='api-debtor-risk-detail'),
    path('kpis/overview/', KpiOverviewAPIView.as_view(), name='api-kpis-overview'),
]
