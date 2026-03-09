from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
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
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if getattr(request.user, 'role', None) not in {'manager', 'admin'}:
            return render(
                request,
                'access_denied.html',
                {
                    'message': 'You do not have permission to access report pages.',
                    'required_role': 'Manager or Admin',
                },
                status=200,
            )

        return super().dispatch(request, *args, **kwargs)


class ManagementReportPreviewView(ManagerOrAdminRequiredMixin, View):
    def get(self, request):
        period_start, period_end = _period_dates(request)
        summary = build_summary(period_start=period_start, period_end=period_end)

        context = {
            'period_start': period_start or 'All Time',
            'period_end': period_end or timezone.localdate(),
            'kpis': summary['kpis'],
            'top_segments': summary['top_segments'][:8],
            'download_excel_url': f"/reports/management/excel/?date_from={period_start or ''}&date_to={period_end or ''}",
            'download_pdf_url': f"/reports/management/pdf/?date_from={period_start or ''}&date_to={period_end or ''}",
        }
        return render(request, 'reports/management_preview.html', context)


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
