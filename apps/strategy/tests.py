from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.portfolio.models import CallLog, Debtor, Portfolio, PromiseToPay
from apps.strategy.models import ActionRule, ActionType
from apps.strategy.services import build_collector_queue, build_strategy_simulator, build_strategy_workspace
from apps.users.models import AppUser, UserRole


class StrategyWorkspaceAccessTests(TestCase):
    def setUp(self):
        self.visitor = AppUser.objects.create_user(username='strategy_visitor', password='DemoPass123!', role=UserRole.VISITOR)
        self.analyst = AppUser.objects.create_user(username='strategy_analyst', password='DemoPass123!', role=UserRole.ANALYST)
        self.manager = AppUser.objects.create_user(username='strategy_manager', password='DemoPass123!', role=UserRole.MANAGER)

    def test_visitor_can_open_strategy_workspace(self):
        self.client.force_login(self.visitor)
        response = self.client.get(reverse('strategy-workspace'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Collections Intelligence')
        self.assertContains(response, 'Next-Best Action Ranking')

    def test_visitor_can_open_collector_queue(self):
        self.client.force_login(self.visitor)
        response = self.client.get(reverse('strategy-queue'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Collector Queue')
        self.assertContains(response, 'Prioritized Assignments')

    def test_visitor_can_open_strategy_simulator(self):
        self.client.force_login(self.visitor)
        response = self.client.get(reverse('strategy-simulator'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Strategy Simulator')
        self.assertContains(response, 'Collections Strategy Comparison')

    def test_visitor_can_open_rules_in_read_only_mode(self):
        self.client.force_login(self.visitor)
        response = self.client.get(reverse('strategy-rules'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Read-Only Rule Review')

    def test_manager_can_create_action_rule(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse('strategy-rules'),
            {
                'name': 'Broken Promise Settlement Rule',
                'risk_band': 'high',
                'debtor_status': 'contacted',
                'dpd_min': 120,
                'dpd_max': 999,
                'requires_phone': True,
                'requires_email': False,
                'recommended_action': ActionType.SETTLEMENT,
                'recommended_channel': ActionType.CALL,
                'base_uplift_pct': '8.50',
                'priority_weight': 82,
                'active': True,
                'notes': 'Escalate broken promise high-balance debtors into settlement review.',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ActionRule.objects.filter(name='Broken Promise Settlement Rule').exists())

    def test_analyst_gets_friendly_denial_for_strategy_workspace(self):
        self.client.force_login(self.analyst)
        response = self.client.get(reverse('strategy-workspace'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'You do not have permission to access this page.')


class StrategyServiceTests(TestCase):
    def setUp(self):
        self.user = AppUser.objects.create_user(username='manager_strategy', password='DemoPass123!', role=UserRole.MANAGER)
        self.portfolio = Portfolio.objects.create(
            name='Strategy Test Portfolio',
            source_company='Test Creditor',
            purchase_date=timezone.localdate(),
            purchase_price=Decimal('120000.00'),
            face_value=Decimal('450000.00'),
            currency='EUR',
            created_by=self.user,
        )

    def test_strategy_workspace_ranks_debtors_and_builds_summary(self):
        high_balance = Debtor.objects.create(
            portfolio=self.portfolio,
            external_id='D-001',
            full_name='High Balance Broken Promise',
            status='contacted',
            days_past_due=150,
            outstanding_principal=Decimal('5000.00'),
            outstanding_total=Decimal('6200.00'),
            risk_score=84,
            risk_band='high',
            phone_number='+359111111',
        )
        PromiseToPay.objects.create(
            debtor=high_balance,
            promised_amount=Decimal('400.00'),
            due_date=timezone.localdate(),
            status=PromiseToPay.PromiseStatus.BROKEN,
        )

        Debtor.objects.create(
            portfolio=self.portfolio,
            external_id='D-002',
            full_name='Low Balance Reachable',
            status='new',
            days_past_due=35,
            outstanding_principal=Decimal('450.00'),
            outstanding_total=Decimal('700.00'),
            risk_score=41,
            risk_band='medium',
            phone_number='+359222222',
        )

        payload = build_strategy_workspace(portfolio=self.portfolio)

        self.assertEqual(payload['summary']['debtor_count'], 2)
        self.assertEqual(payload['recommendations'][0]['recommended_action'], ActionType.SETTLEMENT)
        self.assertEqual(payload['recommendations'][0]['recommended_channel'], ActionType.CALL)
        self.assertGreater(payload['recommendations'][0]['priority_score'], payload['recommendations'][1]['priority_score'])
        self.assertEqual(payload['summary']['highest_value_action'], 'Settlement Offer')

    def test_paying_account_is_recommended_for_monitoring(self):
        Debtor.objects.create(
            portfolio=self.portfolio,
            external_id='D-003',
            full_name='Already Paying Debtor',
            status='paying',
            days_past_due=20,
            outstanding_principal=Decimal('1200.00'),
            outstanding_total=Decimal('1300.00'),
            risk_score=28,
            risk_band='low',
            email='paying@example.com',
        )

        payload = build_strategy_workspace(portfolio=self.portfolio)

        self.assertEqual(payload['recommendations'][0]['recommended_action'], ActionType.MONITOR)
        self.assertEqual(payload['recommendations'][0]['recommended_channel'], ActionType.MONITOR)

    def test_collector_queue_assigns_ranked_cases_into_lanes(self):
        first = Debtor.objects.create(
            portfolio=self.portfolio,
            external_id='D-004',
            full_name='Priority One Debtor',
            status='contacted',
            days_past_due=180,
            outstanding_principal=Decimal('6000.00'),
            outstanding_total=Decimal('7600.00'),
            risk_score=89,
            risk_band='high',
            phone_number='+359333333',
        )
        PromiseToPay.objects.create(
            debtor=first,
            promised_amount=Decimal('500.00'),
            due_date=timezone.localdate(),
            status=PromiseToPay.PromiseStatus.BROKEN,
        )
        Debtor.objects.create(
            portfolio=self.portfolio,
            external_id='D-005',
            full_name='Priority Two Debtor',
            status='new',
            days_past_due=70,
            outstanding_principal=Decimal('1200.00'),
            outstanding_total=Decimal('1500.00'),
            risk_score=58,
            risk_band='medium',
            email='priority2@example.com',
        )

        queue = build_collector_queue(portfolio=self.portfolio)

        self.assertEqual(queue['queue_summary']['queued_cases'], 2)
        self.assertGreaterEqual(len(queue['collector_cards']), 2)
        self.assertEqual(queue['queue_rows'][0]['debtor'], first)
        self.assertEqual(queue['queue_rows'][0]['queue_rank'], 1)
        self.assertIn(queue['queue_rows'][0]['priority_bucket'], {'Act Now', 'Review Today', 'Monitor Queue'})

    def test_strategy_simulator_ranks_scenarios_and_returns_winner(self):
        first = Debtor.objects.create(
            portfolio=self.portfolio,
            external_id='D-006',
            full_name='Settlement Debtor',
            status='contacted',
            days_past_due=170,
            outstanding_principal=Decimal('5800.00'),
            outstanding_total=Decimal('6900.00'),
            risk_score=87,
            risk_band='high',
            phone_number='+359444444',
        )
        PromiseToPay.objects.create(
            debtor=first,
            promised_amount=Decimal('450.00'),
            due_date=timezone.localdate(),
            status=PromiseToPay.PromiseStatus.BROKEN,
        )
        Debtor.objects.create(
            portfolio=self.portfolio,
            external_id='D-007',
            full_name='Digital Debtor',
            status='new',
            days_past_due=95,
            outstanding_principal=Decimal('1500.00'),
            outstanding_total=Decimal('1900.00'),
            risk_score=60,
            risk_band='medium',
            email='digital@example.com',
        )

        payload = build_strategy_simulator(portfolio=self.portfolio)

        self.assertEqual(payload['simulator_summary']['strategy_count'], 5)
        self.assertIsNotNone(payload['winner'])
        self.assertEqual(payload['strategy_rows'][0]['label'], payload['winner']['label'])
        self.assertGreaterEqual(payload['winner']['expected_roi'], payload['strategy_rows'][-1]['expected_roi'])
        self.assertGreaterEqual(payload['winner']['debtor_count'], 0)


    def test_repeated_no_answer_calls_shift_action_away_from_call(self):
        debtor = Debtor.objects.create(
            portfolio=self.portfolio,
            external_id='D-008',
            full_name='Unanswered Call Debtor',
            status='contacted',
            days_past_due=125,
            outstanding_principal=Decimal('2400.00'),
            outstanding_total=Decimal('2800.00'),
            risk_score=72,
            risk_band='high',
            phone_number='+359666666',
            email='unanswered@example.com',
        )
        for idx in range(3):
            CallLog.objects.create(
                debtor=debtor,
                agent=self.user,
                call_datetime=timezone.now(),
                outcome=CallLog.Outcome.NO_ANSWER,
                duration_seconds=0,
                notes=f'No answer attempt {idx + 1}',
            )

        payload = build_strategy_workspace(portfolio=self.portfolio)

        self.assertEqual(payload['recommendations'][0]['recommended_action'], ActionType.EMAIL)
        self.assertEqual(payload['recommendations'][0]['no_answer_streak'], 3)
        self.assertEqual(payload['recommendations'][0]['call_attempt_count'], 3)

    def test_repeated_wrong_contact_moves_case_to_monitor(self):
        debtor = Debtor.objects.create(
            portfolio=self.portfolio,
            external_id='D-009',
            full_name='Wrong Contact Debtor',
            status='contacted',
            days_past_due=210,
            outstanding_principal=Decimal('1600.00'),
            outstanding_total=Decimal('2100.00'),
            risk_score=75,
            risk_band='high',
            phone_number='+359777777',
        )
        for idx in range(2):
            CallLog.objects.create(
                debtor=debtor,
                agent=self.user,
                call_datetime=timezone.now(),
                outcome=CallLog.Outcome.WRONG_CONTACT,
                duration_seconds=25,
                notes=f'Wrong contact {idx + 1}',
            )

        payload = build_strategy_workspace(portfolio=self.portfolio)
        recommendation = payload['recommendations'][0]

        self.assertEqual(recommendation['recommended_action'], ActionType.MONITOR)
        self.assertEqual(recommendation['wrong_contact_count'], 2)

    def test_recent_promise_to_pay_call_keeps_follow_up_action(self):
        debtor = Debtor.objects.create(
            portfolio=self.portfolio,
            external_id='D-010',
            full_name='Promise Follow Up Debtor',
            status='contacted',
            days_past_due=95,
            outstanding_principal=Decimal('2200.00'),
            outstanding_total=Decimal('2500.00'),
            risk_score=67,
            risk_band='medium',
            phone_number='+359888888',
        )
        call = CallLog.objects.create(
            debtor=debtor,
            agent=self.user,
            call_datetime=timezone.now(),
            outcome=CallLog.Outcome.PROMISE_TO_PAY,
            duration_seconds=180,
            promised_amount=Decimal('300.00'),
            notes='Debtor promised a partial payment next week.',
        )
        PromiseToPay.objects.create(
            debtor=debtor,
            call_log=call,
            promised_amount=Decimal('300.00'),
            due_date=timezone.localdate(),
            status=PromiseToPay.PromiseStatus.PENDING,
            notes='Needs follow-up call before due date.',
        )

        payload = build_strategy_workspace(portfolio=self.portfolio)
        recommendation = payload['recommendations'][0]

        self.assertEqual(recommendation['recommended_action'], ActionType.CALL)
        self.assertEqual(recommendation['last_call_outcome'], CallLog.Outcome.PROMISE_TO_PAY)
        self.assertEqual(recommendation['pending_promises'], 1)
