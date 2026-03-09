from django.urls import path

from apps.reports.views import ManagementExcelReportView, ManagementPdfReportView, ManagementReportPreviewView


urlpatterns = [
    path('management/', ManagementReportPreviewView.as_view(), name='report-management-preview'),
    path('management/excel/', ManagementExcelReportView.as_view(), name='report-management-excel'),
    path('management/pdf/', ManagementPdfReportView.as_view(), name='report-management-pdf'),
]
