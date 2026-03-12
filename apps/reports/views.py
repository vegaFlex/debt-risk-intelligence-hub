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


def _access_denied(request, message, required_role, primary_action=None):
    return render(
        request,
        'access_denied.html',
        {
            'message': message,
            'required_role': required_role,
            'primary_action': primary_action or {'label': 'Back to Home', 'url': '/', 'style': 'btn-secondary'},
        },
        status=200,
    )


class ManagerOrAdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if getattr(request.user, 'role', None) not in {'manager', 'admin'}:
            message = 'You do not have permission to access report pages.'
            if getattr(request.user, 'role', None) == 'visitor':
                message = 'This demo account is view-only. You can review reports here, but only manager or admin accounts can generate or export them.'
            return _access_denied(
                request,
                message,
                'Manager or Admin',
                primary_action={'label': 'Open Report Preview', 'url': '/reports/management/', 'style': 'btn-secondary'},
            )

        return super().dispatch(request, *args, **kwargs)


class ViewerOrManagerOrAdminReadOnlyMixin(LoginRequiredMixin):
    safe_methods = {'GET', 'HEAD', 'OPTIONS'}

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        role = getattr(request.user, 'role', None)
        if role not in {'visitor', 'manager', 'admin'}:
            return _access_denied(
                request,
                'You do not have permission to access this page.',
                'Visitor, Manager or Admin',
                primary_action={'label': 'Back to Home', 'url': '/', 'style': 'btn-secondary'},
            )

        if role == 'visitor' and request.method not in self.safe_methods:
            return _access_denied(
                request,
                'This demo account is view-only. Sign in with a manager or admin account to make changes.',
                'Manager or Admin for changes',
                primary_action={'label': 'Back to Home', 'url': '/', 'style': 'btn-secondary'},
            )

        return super().dispatch(request, *args, **kwargs)


class ManagementReportPreviewView(ViewerOrManagerOrAdminReadOnlyMixin, View):
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
            'can_export_reports': getattr(request.user, 'role', None) in {'manager', 'admin'},
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
