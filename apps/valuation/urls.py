from django.urls import path

from apps.valuation.views import (
    HistoricalBenchmarkEditView,
    HistoricalBenchmarkListView,
    PortfolioValuationPreviewView,
    RunPortfolioValuationView,
    ValuationExcelReportView,
    ValuationImportView,
    ValuationPdfReportView,
    ValuationReportPreviewView,
    ValuationWorkspaceView,
)


urlpatterns = [
    path('', ValuationWorkspaceView.as_view(), name='valuation-workspace'),
    path('import/', ValuationImportView.as_view(), name='valuation-import'),
    path('benchmarks/', HistoricalBenchmarkListView.as_view(), name='valuation-benchmarks'),
    path('benchmarks/<int:benchmark_id>/edit/', HistoricalBenchmarkEditView.as_view(), name='valuation-benchmark-edit'),
    path('portfolio/<int:portfolio_id>/', PortfolioValuationPreviewView.as_view(), name='valuation-preview'),
    path('portfolio/<int:portfolio_id>/run/', RunPortfolioValuationView.as_view(), name='valuation-run'),
    path('portfolio/<int:portfolio_id>/report/', ValuationReportPreviewView.as_view(), name='valuation-report-preview'),
    path('portfolio/<int:portfolio_id>/report/excel/', ValuationExcelReportView.as_view(), name='valuation-report-excel'),
    path('portfolio/<int:portfolio_id>/report/pdf/', ValuationPdfReportView.as_view(), name='valuation-report-pdf'),
]
