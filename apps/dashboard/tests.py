from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.portfolio.models import Debtor, Payment, Portfolio
from apps.users.models import AppUser


class DashboardViewTests(TestCase):
    def setUp(self):
        self.analyst = AppUser.objects.create_user(username='analyst_dash', password='pass123', role='analyst')
        self.manager = AppUser.objects.create_user(username='manager_dash', password='pass123', role='manager')

        self.portfolio_one = Portfolio.objects.create(
            name='Portfolio One',
            source_company='U1',
            purchase_date=date(2026, 3, 1),
            purchase_price=Decimal('1000'),
            face_value=Decimal('5000'),
            currency='BGN',
        )

        self.debtor_a = Debtor.objects.create(
            portfolio=self.portfolio_one,
            external_id='P1-001',
            full_name='Debtor A',
            status='paying',
            days_past_due=150,
            outstanding_principal=Decimal('1400'),
            outstanding_total=Decimal('1600'),
            risk_score=72,
            risk_band='high',
            risk_factors='sample',
        )

        Payment.objects.create(
            debtor=self.debtor_a,
            paid_amount=Decimal('300'),
            payment_date=date(2026, 3, 8),
            channel='bank_transfer',
            reference='PMT-001',
            is_confirmed=True,
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard-home'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_forbidden_for_analyst(self):
        self.client.login(username='analyst_dash', password='pass123')
        response = self.client.get(reverse('dashboard-home'))
        self.assertEqual(response.status_code, 403)

    def test_dashboard_allowed_for_manager(self):
        self.client.login(username='manager_dash', password='pass123')
        response = self.client.get(reverse('dashboard-home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Debt & Risk Dashboard')
