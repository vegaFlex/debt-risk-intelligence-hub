from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.portfolio.models import Debtor, Payment, Portfolio


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
        Debtor.objects.create(
            portfolio=self.portfolio_two,
            external_id='P2-002',
            full_name='Debtor C',
            status='new',
            days_past_due=12,
            outstanding_principal=Decimal('180'),
            outstanding_total=Decimal('220'),
            risk_score=22,
            risk_band='low',
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

    def test_dashboard_page_loads(self):
        response = self.client.get(reverse('dashboard-home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Debt & Risk Dashboard')
        self.assertContains(response, 'Call Center Performance')
        self.assertContains(response, 'Conversion Rate')

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

    def test_dashboard_performance_metrics_in_context(self):
        response = self.client.get(reverse('dashboard-home'))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context['performance']['contacted_count'], 2)
        self.assertEqual(response.context['performance']['ptp_count'], 0)
        self.assertEqual(response.context['performance']['paying_count'], 1)
        self.assertEqual(response.context['performance']['open_cases'], 3)
        self.assertEqual(response.context['kpis']['conversion_rate'], 50.0)

    def test_dashboard_has_top_risk_segments(self):
        response = self.client.get(reverse('dashboard-home'))
        self.assertEqual(response.status_code, 200)
        segments = list(response.context['top_risk_segments'])
        self.assertGreaterEqual(len(segments), 1)
        self.assertIn('portfolio__name', segments[0])
        self.assertIn('risk_band', segments[0])
        self.assertIn('debtor_count', segments[0])
