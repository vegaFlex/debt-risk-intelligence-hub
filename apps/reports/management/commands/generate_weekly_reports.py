from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.reports.models import GeneratedReport
from apps.reports.services import build_excel_report, build_pdf_report, build_summary


class Command(BaseCommand):
    help = 'Generate weekly management summary reports in Excel and PDF.'

    def handle(self, *args, **options):
        end_date = timezone.localdate()
        start_date = end_date - timedelta(days=6)

        summary = build_summary(period_start=start_date, period_end=end_date)

        reports_dir = Path(settings.BASE_DIR) / 'generated_reports'
        reports_dir.mkdir(parents=True, exist_ok=True)

        stamp = timezone.now().strftime('%Y%m%d_%H%M%S')

        excel_name = f'weekly_management_{stamp}.xlsx'
        excel_path = reports_dir / excel_name
        excel_path.write_bytes(build_excel_report(summary))

        GeneratedReport.objects.create(
            report_type=GeneratedReport.ReportType.MANAGEMENT_WEEKLY,
            report_format=GeneratedReport.ReportFormat.XLSX,
            status=GeneratedReport.Status.SUCCESS,
            period_start=start_date,
            period_end=end_date,
            file_name=excel_name,
            file_path=str(excel_path),
            details='Generated via management command: generate_weekly_reports',
        )

        pdf_name = f'weekly_management_{stamp}.pdf'
        pdf_path = reports_dir / pdf_name
        period_label = f'{start_date} - {end_date}'
        pdf_path.write_bytes(build_pdf_report(summary, period_label=period_label))

        GeneratedReport.objects.create(
            report_type=GeneratedReport.ReportType.MANAGEMENT_WEEKLY,
            report_format=GeneratedReport.ReportFormat.PDF,
            status=GeneratedReport.Status.SUCCESS,
            period_start=start_date,
            period_end=end_date,
            file_name=pdf_name,
            file_path=str(pdf_path),
            details='Generated via management command: generate_weekly_reports',
        )

        self.stdout.write(self.style.SUCCESS(f'Created reports: {excel_name}, {pdf_name}'))
