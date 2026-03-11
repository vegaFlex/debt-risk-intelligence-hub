from django.urls import path

from apps.valuation.views import (
    PortfolioValuationPreviewView,
    RunPortfolioValuationView,
    ValuationWorkspaceView,
)


urlpatterns = [
    path('', ValuationWorkspaceView.as_view(), name='valuation-workspace'),
    path('portfolio/<int:portfolio_id>/', PortfolioValuationPreviewView.as_view(), name='valuation-preview'),
    path('portfolio/<int:portfolio_id>/run/', RunPortfolioValuationView.as_view(), name='valuation-run'),
]
