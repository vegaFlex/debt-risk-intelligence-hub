from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils import timezone
from django.views import View

from apps.reports.models import GeneratedReport
from apps.reports.services import build_excel_report, build_pdf_report, build_summary


def _period_dates(request):
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    return date_from or None, date_to or None


class ManagerOrAdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if getattr(request.user, 'role', None) not in {'manager', 'admin'}:
            raise PermissionDenied('Manager or Admin role required.')
        return super().dispatch(request, *args, **kwargs)


class ManagementExcelReportView(ManagerOrAdminRequiredMixin, View):
    def get(self, request):
        period_start, period_end = _period_dates(request)
        summary = build_summary(period_start=period_start, period_end=period_end)
        content = build_excel_report(summary)

        stamp = timezone.now().strftime('%Y%m%d_%H%M')
        file_name = f'management_report_{stamp}.xlsx'

        GeneratedReport.objects.create(
            report_type=GeneratedReport.ReportType.MANAGEMENT_WEEKLY,
            report_format=GeneratedReport.ReportFormat.XLSX,
            status=GeneratedReport.Status.SUCCESS,
            period_start=period_start or date(2000, 1, 1),
            period_end=period_end or timezone.localdate(),
            file_name=file_name,
            file_path='downloaded-via-web',
            created_by=request.user if request.user.is_authenticated else None,
            details='Excel report generated from dashboard filters.',
        )

        response = HttpResponse(
            content,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename={file_name}'
        return response


class ManagementPdfReportView(ManagerOrAdminRequiredMixin, View):
    def get(self, request):
        period_start, period_end = _period_dates(request)
        summary = build_summary(period_start=period_start, period_end=period_end)

        label = f'{period_start or "All Time"} - {period_end or timezone.localdate()}'
        content = build_pdf_report(summary, period_label=label)

        stamp = timezone.now().strftime('%Y%m%d_%H%M')
        file_name = f'management_report_{stamp}.pdf'

        GeneratedReport.objects.create(
            report_type=GeneratedReport.ReportType.MANAGEMENT_WEEKLY,
            report_format=GeneratedReport.ReportFormat.PDF,
            status=GeneratedReport.Status.SUCCESS,
            period_start=period_start or date(2000, 1, 1),
            period_end=period_end or timezone.localdate(),
            file_name=file_name,
            file_path='downloaded-via-web',
            created_by=request.user if request.user.is_authenticated else None,
            details='PDF report generated from dashboard filters.',
        )

        response = HttpResponse(content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename={file_name}'
        return response
