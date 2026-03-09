from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.portfolio.models import Debtor, Payment, Portfolio
from apps.users.models import AppUser


class PortfolioApiTests(APITestCase):
    def setUp(self):
        self.analyst = AppUser.objects.create_user(username='analyst', password='pass123', role='analyst')
        self.manager = AppUser.objects.create_user(username='manager', password='pass123', role='manager')

        self.portfolio = Portfolio.objects.create(
            name='March Debt Batch',
            source_company='UBB',
            purchase_date=date(2026, 3, 1),
            purchase_price=Decimal('15000'),
            face_value=Decimal('60000'),
            currency='BGN',
        )

        self.high = Debtor.objects.create(
            portfolio=self.portfolio,
            external_id='D-001',
            full_name='High Risk Debtor',
            status='new',
            days_past_due=210,
            outstanding_principal=Decimal('5500'),
            outstanding_total=Decimal('6000'),
            risk_score=88,
            risk_band='high',
            risk_factors='days_past_due >= 180',
        )
        Debtor.objects.create(
            portfolio=self.portfolio,
            external_id='D-002',
            full_name='Medium Risk Debtor',
            status='promise_to_pay',
            days_past_due=60,
            outstanding_principal=Decimal('900'),
            outstanding_total=Decimal('1200'),
            risk_score=52,
            risk_band='medium',
            risk_factors='days_past_due >= 30',
        )
        Payment.objects.create(
            debtor=self.high,
            paid_amount=Decimal('300'),
            payment_date=date(2026, 3, 8),
            channel='bank_transfer',
            reference='PMT-001',
            is_confirmed=True,
        )

    def test_portfolios_list_endpoint_requires_auth(self):
        response = self.client.get(reverse('api-portfolios-list'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_portfolios_list_endpoint_for_analyst(self):
        self.client.force_authenticate(user=self.analyst)
        response = self.client.get(reverse('api-portfolios-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['debtors_count'], 2)

    def test_debtors_filter_by_risk_band(self):
        self.client.force_authenticate(user=self.analyst)
        response = self.client.get(reverse('api-debtors-list'), {'risk_band': 'high'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['external_id'], 'D-001')

    def test_kpi_overview_forbidden_for_analyst(self):
        self.client.force_authenticate(user=self.analyst)
        response = self.client.get(reverse('api-kpis-overview'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_kpi_overview_allowed_for_manager(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.get(reverse('api-kpis-overview'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_debtors'], 2)
        self.assertIn('contact_rate', response.data)
        self.assertIn('ptp_rate', response.data)
        self.assertIn('recovery_rate', response.data)
        self.assertIn('expected_collections', response.data)
