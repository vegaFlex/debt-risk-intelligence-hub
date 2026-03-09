from datetime import date
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.portfolio.models import Debtor, Payment, Portfolio
from apps.reports.models import GeneratedReport
from apps.reports.services import build_summary
from apps.users.models import AppUser


class ReportsModuleTests(TestCase):
    def setUp(self):
        self.analyst = AppUser.objects.create_user(username='analyst_report', password='pass123', role='analyst')
        self.manager = AppUser.objects.create_user(username='manager_report', password='pass123', role='manager')

        self.portfolio = Portfolio.objects.create(
            name='Report Portfolio',
            source_company='U1',
            purchase_date=date(2026, 3, 1),
            purchase_price=Decimal('1000'),
            face_value=Decimal('5000'),
            currency='BGN',
        )
        self.debtor = Debtor.objects.create(
            portfolio=self.portfolio,
            external_id='R-001',
            full_name='Report Debtor',
            status='paying',
            days_past_due=120,
            outstanding_principal=Decimal('1000'),
            outstanding_total=Decimal('1200'),
            risk_score=70,
            risk_band='high',
            risk_factors='sample',
        )
        Payment.objects.create(
            debtor=self.debtor,
            paid_amount=Decimal('250'),
            payment_date=date.today(),
            channel='bank_transfer',
            reference='PAY-001',
            is_confirmed=True,
        )

    def tearDown(self):
        generated = Path(settings.BASE_DIR) / 'generated_reports'
        if generated.exists():
            for item in generated.glob('weekly_management_*'):
                item.unlink(missing_ok=True)

    def test_build_summary_contains_expected_kpis(self):
        summary = build_summary()
        self.assertIn('kpis', summary)
        self.assertIn('top_segments', summary)
        self.assertEqual(summary['kpis']['total_debtors'], 1)

    def test_excel_report_forbidden_for_analyst(self):
        self.client.login(username='analyst_report', password='pass123')
        response = self.client.get(reverse('report-management-excel'))
        self.assertEqual(response.status_code, 403)

    def test_excel_report_allowed_for_manager(self):
        self.client.login(username='manager_report', password='pass123')
        response = self.client.get(reverse('report-management-excel'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    def test_pdf_report_allowed_for_manager(self):
        self.client.login(username='manager_report', password='pass123')
        response = self.client.get(reverse('report-management-pdf'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_weekly_report_management_command_creates_files_and_logs(self):
        call_command('generate_weekly_reports')
        generated = Path(settings.BASE_DIR) / 'generated_reports'

        self.assertTrue(generated.exists())
        self.assertGreaterEqual(len(list(generated.glob('weekly_management_*.xlsx'))), 1)
        self.assertGreaterEqual(len(list(generated.glob('weekly_management_*.pdf'))), 1)
        self.assertGreaterEqual(GeneratedReport.objects.count(), 2)
