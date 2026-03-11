from django.urls import path

from apps.valuation.views import (
    HistoricalBenchmarkEditView,
    HistoricalBenchmarkListView,
    PortfolioValuationPreviewView,
    RunPortfolioValuationView,
    ValuationImportView,
    ValuationWorkspaceView,
)


urlpatterns = [
    path('', ValuationWorkspaceView.as_view(), name='valuation-workspace'),
    path('import/', ValuationImportView.as_view(), name='valuation-import'),
    path('benchmarks/', HistoricalBenchmarkListView.as_view(), name='valuation-benchmarks'),
    path('benchmarks/<int:benchmark_id>/edit/', HistoricalBenchmarkEditView.as_view(), name='valuation-benchmark-edit'),
    path('portfolio/<int:portfolio_id>/', PortfolioValuationPreviewView.as_view(), name='valuation-preview'),
    path('portfolio/<int:portfolio_id>/run/', RunPortfolioValuationView.as_view(), name='valuation-run'),
]
