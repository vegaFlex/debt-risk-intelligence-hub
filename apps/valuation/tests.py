from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.portfolio.models import Debtor, Payment, Portfolio
from apps.valuation.models import Creditor, PortfolioValuation, ValuationFactor
from apps.valuation.services import build_rule_based_valuation, persist_rule_based_valuation


class CreditorModelTests(TestCase):
    def test_string_representation_returns_name(self):
        creditor = Creditor.objects.create(name='Test Creditor')

        self.assertEqual(str(creditor), 'Test Creditor')


class RuleBasedValuationServiceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='valuation_user',
            password='DemoPass123!',
            role='manager',
        )
        self.creditor = Creditor.objects.create(name='Vivus Proxy', category=Creditor.Category.FINTECH)
        self.portfolio = Portfolio.objects.create(
            name='Valuation Test Portfolio',
            source_company='Demo Source',
            purchase_date=date(2026, 3, 11),
            purchase_price=Decimal('25000.00'),
            face_value=Decimal('120000.00'),
            currency='EUR',
            created_by=self.user,
        )

        Debtor.objects.create(
            portfolio=self.portfolio,
            external_id='VAL-001',
            full_name='High Risk Debtor',
            status='new',
            days_past_due=220,
            outstanding_principal=Decimal('6100.00'),
            outstanding_total=Decimal('6800.00'),
            risk_score=91,
            risk_band='high',
            phone_number='0888000001',
        )
        Debtor.objects.create(
            portfolio=self.portfolio,
            external_id='VAL-002',
            full_name='Promise Debtor',
            status='promise_to_pay',
            days_past_due=95,
            outstanding_principal=Decimal('1800.00'),
            outstanding_total=Decimal('2150.00'),
            risk_score=63,
            risk_band='medium',
            email='promise@example.com',
        )
        paying_debtor = Debtor.objects.create(
            portfolio=self.portfolio,
            external_id='VAL-003',
            full_name='Paying Debtor',
            status='paying',
            days_past_due=24,
            outstanding_principal=Decimal('450.00'),
            outstanding_total=Decimal('520.00'),
            risk_score=28,
            risk_band='low',
            phone_number='0888000003',
            email='paying@example.com',
        )

        Payment.objects.create(
            debtor=paying_debtor,
            paid_amount=Decimal('120.00'),
            payment_date=date(2026, 3, 10),
            channel='bank_transfer',
        )

    def test_build_rule_based_valuation_returns_expected_metrics_and_factors(self):
        result = build_rule_based_valuation(self.portfolio)

        self.assertEqual(result['portfolio'], self.portfolio)
        self.assertEqual(result['face_value'], Decimal('120000.00'))
        self.assertGreater(result['expected_recovery_rate'], Decimal('0.00'))
        self.assertGreater(result['expected_collections'], Decimal('0.00'))
        self.assertGreaterEqual(result['recommended_bid_pct'], Decimal('3.00'))
        self.assertGreater(result['recommended_bid_amount'], Decimal('0.00'))
        self.assertGreater(result['confidence_score'], Decimal('0.00'))
        self.assertEqual(result['stats']['total_debtors'], 3)
        self.assertGreaterEqual(len(result['factors']), 6)
        self.assertIn('high_risk_concentration', {factor['factor_name'] for factor in result['factors']})
        self.assertIn('contactability', {factor['factor_name'] for factor in result['factors']})

    def test_persist_rule_based_valuation_creates_valuation_and_factor_rows(self):
        valuation = persist_rule_based_valuation(
            self.portfolio,
            creditor=self.creditor,
            created_by=self.user,
        )

        self.assertIsInstance(valuation, PortfolioValuation)
        self.assertEqual(valuation.portfolio, self.portfolio)
        self.assertEqual(valuation.creditor, self.creditor)
        self.assertEqual(valuation.created_by, self.user)
        self.assertEqual(valuation.valuation_method, PortfolioValuation.ValuationMethod.RULE_BASED)
        self.assertGreater(ValuationFactor.objects.filter(valuation=valuation).count(), 0)
