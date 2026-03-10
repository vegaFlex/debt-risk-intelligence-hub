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

        self.debtor_b = Debtor.objects.create(
            portfolio=self.portfolio_one,
            external_id='P1-002',
            full_name='Debtor B',
            status='new',
            days_past_due=20,
            outstanding_principal=Decimal('300'),
            outstanding_total=Decimal('360'),
            risk_score=35,
            risk_band='low',
            risk_factors='sample',
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard-home'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_shows_access_restricted_for_analyst(self):
        self.client.login(username='analyst_dash', password='pass123')
        response = self.client.get(reverse('dashboard-home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Access Restricted')

    def test_dashboard_allowed_for_manager(self):
        self.client.login(username='manager_dash', password='pass123')
        response = self.client.get(reverse('dashboard-home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Full Debtor List')
        self.assertContains(response, 'Report Preview')
        self.assertContains(response, 'More Actions')
        self.assertContains(response, 'Priority Debtor Preview')
        self.assertContains(response, 'Risk Segment Breakdown')

    def test_dashboard_filters_by_selected_status(self):
        self.client.login(username='manager_dash', password='pass123')
        response = self.client.get(reverse('dashboard-home'), {'status': 'paying'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Debtor A')
        self.assertNotContains(response, 'Debtor B')

    def test_dashboard_ignores_invalid_status_filter(self):
        self.client.login(username='manager_dash', password='pass123')
        response = self.client.get(reverse('dashboard-home'), {'status': 'not_real_status'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['filters']['status'], '')
        self.assertContains(response, 'Debtor A')
        self.assertContains(response, 'Debtor B')

    def test_dashboard_filters_by_portfolio_and_risk_band(self):
        self.client.login(username='manager_dash', password='pass123')
        response = self.client.get(reverse('dashboard-home'), {'portfolio': self.portfolio_one.id, 'risk_band': 'low'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['kpis']['total_debtors'], 1)
        self.assertContains(response, 'Debtor B')
        self.assertNotContains(response, 'Debtor A')

    def test_full_list_sorts_results_by_requested_column(self):
        self.client.login(username='manager_dash', password='pass123')
        response = self.client.get(reverse('dashboard-debtor-results'), {'sort': 'outstanding_total', 'direction': 'asc'})
        self.assertEqual(response.status_code, 200)
        results = list(response.context['results_page'].object_list)
        self.assertEqual(results[0].external_id, 'P1-002')
        self.assertEqual(results[1].external_id, 'P1-001')
        self.assertContains(response, 'Sortable Debtor Results')

    def test_full_list_paginates_results(self):
        for idx in range(3, 31):
            Debtor.objects.create(
                portfolio=self.portfolio_one,
                external_id=f'P1-{idx:03d}',
                full_name=f'Debtor {idx}',
                status='contacted',
                days_past_due=30 + idx,
                outstanding_principal=Decimal('200'),
                outstanding_total=Decimal('250'),
                risk_score=25,
                risk_band='low',
                risk_factors='sample',
            )

        self.client.login(username='manager_dash', password='pass123')
        response = self.client.get(reverse('dashboard-debtor-results'), {'page': 2, 'sort': 'full_name', 'direction': 'asc'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['results_page'].number, 2)
        self.assertEqual(response.context['results_page'].paginator.num_pages, 2)
        self.assertContains(response, '15 debtors per page')
