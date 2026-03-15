from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.portfolio.models import Debtor, Portfolio, PromiseToPay
from apps.users.models import AppUser, UserRole


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class StrategyApiTests(TestCase):
    def setUp(self):
        self.visitor = AppUser.objects.create_user(username='api_visitor', password='DemoPass123!', role=UserRole.VISITOR)
        self.analyst = AppUser.objects.create_user(username='api_analyst', password='DemoPass123!', role=UserRole.ANALYST)
        self.manager = AppUser.objects.create_user(username='api_manager', password='DemoPass123!', role=UserRole.MANAGER)
        self.portfolio = Portfolio.objects.create(
            name='API Strategy Portfolio',
            source_company='API Creditor',
            purchase_date=timezone.localdate(),
            purchase_price=Decimal('90000.00'),
            face_value=Decimal('250000.00'),
            currency='EUR',
            created_by=self.manager,
        )
        debtor = Debtor.objects.create(
            portfolio=self.portfolio,
            external_id='API-001',
            full_name='API Broken Promise Debtor',
            status='contacted',
            days_past_due=145,
            outstanding_principal=Decimal('4200.00'),
            outstanding_total=Decimal('5400.00'),
            risk_score=82,
            risk_band='high',
            phone_number='+359555555',
        )
        PromiseToPay.objects.create(
            debtor=debtor,
            promised_amount=Decimal('350.00'),
            due_date=timezone.localdate(),
            status=PromiseToPay.PromiseStatus.BROKEN,
        )

    def test_visitor_can_read_strategy_recommendations_api(self):
        self.client.force_login(self.visitor)
        response = self.client.get(reverse('api-strategy-recommendations'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('summary', response.json())
        self.assertIn('results', response.json())
        self.assertEqual(response.json()['summary']['debtor_count'], 1)

    def test_visitor_can_read_strategy_queue_api(self):
        self.client.force_login(self.visitor)
        response = self.client.get(reverse('api-strategy-queue'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['summary']['queued_cases'], 1)
        self.assertEqual(len(response.json()['results']), 1)

    def test_visitor_can_read_strategy_simulator_api(self):
        self.client.force_login(self.visitor)
        response = self.client.get(reverse('api-strategy-simulator'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['summary']['strategy_count'], 5)
        self.assertEqual(len(response.json()['results']), 5)

    def test_analyst_cannot_read_strategy_api(self):
        self.client.force_login(self.analyst)
        response = self.client.get(reverse('api-strategy-recommendations'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['access'], False)
        self.assertIn('permission', response.json()['message'].lower())
