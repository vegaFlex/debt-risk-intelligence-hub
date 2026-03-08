from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.portfolio.models import Debtor, Portfolio


class DashboardViewTests(TestCase):
    def setUp(self):
        self.portfolio_one = Portfolio.objects.create(
            name='Portfolio One',
            source_company='U1',
            purchase_date=date(2026, 3, 1),
            purchase_price=Decimal('1000'),
            face_value=Decimal('5000'),
            currency='BGN',
        )
        self.portfolio_two = Portfolio.objects.create(
            name='Portfolio Two',
            source_company='U2',
            purchase_date=date(2026, 3, 2),
            purchase_price=Decimal('2000'),
            face_value=Decimal('7000'),
            currency='BGN',
        )

        Debtor.objects.create(
            portfolio=self.portfolio_one,
            external_id='P1-001',
            full_name='Debtor A',
            status='new',
            days_past_due=150,
            outstanding_principal=Decimal('1400'),
            outstanding_total=Decimal('1600'),
            risk_score=72,
            risk_band='high',
            risk_factors='sample',
        )
        Debtor.objects.create(
            portfolio=self.portfolio_two,
            external_id='P2-001',
            full_name='Debtor B',
            status='contacted',
            days_past_due=40,
            outstanding_principal=Decimal('400'),
            outstanding_total=Decimal('500'),
            risk_score=43,
            risk_band='medium',
            risk_factors='sample',
        )

    def test_dashboard_page_loads(self):
        response = self.client.get(reverse('dashboard-home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Debt & Risk Dashboard')
        self.assertContains(response, 'Total Debtors')

    def test_dashboard_filter_by_portfolio(self):
        response = self.client.get(reverse('dashboard-home'), {'portfolio': self.portfolio_one.id})
        self.assertEqual(response.status_code, 200)
        debtors = response.context['top_risk_debtors']
        self.assertEqual(len(debtors), 1)
        self.assertEqual(debtors[0].external_id, 'P1-001')

    def test_dashboard_filter_by_risk_band(self):
        response = self.client.get(reverse('dashboard-home'), {'risk_band': 'high'})
        self.assertEqual(response.status_code, 200)
        debtors = response.context['top_risk_debtors']
        self.assertEqual(len(debtors), 1)
        self.assertEqual(debtors[0].risk_band, 'high')
