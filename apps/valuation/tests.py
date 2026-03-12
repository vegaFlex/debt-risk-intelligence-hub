from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.portfolio.models import Debtor, Payment, Portfolio
from apps.valuation.models import Creditor, HistoricalBenchmark, ModelPredictionLog, PortfolioUploadBatch, PortfolioValuation, ValuationFactor
from apps.reports.models import GeneratedReport
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
        self.assertEqual(result['valuation_method'], PortfolioValuation.ValuationMethod.RULE_BASED)
        self.assertIsNone(result['benchmark_context'])
        self.assertEqual(len(result['scenarios']), 4)
        self.assertTrue(any(scenario['is_recommended'] for scenario in result['scenarios']))
        self.assertEqual(set(result['visuals'].keys()), {'risk_mix', 'recovery_bridge', 'operating_signals', 'scenario_roi'})
        self.assertEqual(len(result['visuals']['risk_mix']), 3)
        self.assertEqual(len(result['visuals']['scenario_roi']), 4)
        self.assertEqual(set(result['features'].keys()), {'vector', 'groups', 'dominant_region'})
        self.assertEqual(len(result['features']['groups']), 4)
        self.assertIn('avg_balance', result['features']['vector'])
        self.assertIn('purchase_price_pct_of_face', result['features']['vector'])
        self.assertIn('ml_baseline', result)
        self.assertEqual(result['ml_baseline']['model_version'], 'baseline_v1_proxy')
        self.assertGreater(result['ml_baseline']['predicted_recovery_rate'], Decimal('0.00'))
        self.assertGreaterEqual(len(result['ml_baseline']['top_signals']), 1)

    def test_benchmark_fallback_blends_recovery_and_switches_to_hybrid(self):
        HistoricalBenchmark.objects.create(
            creditor_category=Creditor.Category.FINTECH,
            dpd_band='90-179 days',
            balance_band='2000-4999',
            avg_recovery_rate=Decimal('44.00'),
            avg_contact_rate=Decimal('68.00'),
            avg_ptp_rate=Decimal('21.00'),
            avg_conversion_rate=Decimal('15.00'),
            sample_size=240,
        )

        result = build_rule_based_valuation(self.portfolio, creditor=self.creditor)

        self.assertEqual(result['valuation_method'], PortfolioValuation.ValuationMethod.HYBRID)
        self.assertIsNotNone(result['benchmark_context'])
        self.assertEqual(result['benchmark_context']['source'], 'category_fallback')
        self.assertEqual(result['benchmark_context']['sample_size'], 240)
        self.assertIn('historical_benchmark', {factor['factor_name'] for factor in result['factors']})
        self.assertEqual(len(result['scenarios']), 4)
        self.assertTrue(any(scenario['is_recommended'] for scenario in result['scenarios']))

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
        self.assertEqual(ModelPredictionLog.objects.filter(valuation=valuation).count(), 4)
        self.assertTrue(ModelPredictionLog.objects.filter(valuation=valuation, model_version='baseline_v1_proxy').exists())

    def test_similarity_fallback_uses_closest_comparable_benchmark(self):
        HistoricalBenchmark.objects.create(
            creditor_category=Creditor.Category.FINTECH,
            dpd_band='180+ days',
            balance_band='5000+',
            region='Varna',
            avg_recovery_rate=Decimal('31.00'),
            avg_contact_rate=Decimal('52.00'),
            avg_ptp_rate=Decimal('16.00'),
            avg_conversion_rate=Decimal('11.00'),
            sample_size=130,
        )

        result = build_rule_based_valuation(self.portfolio, creditor=self.creditor)

        self.assertEqual(result['valuation_method'], PortfolioValuation.ValuationMethod.HYBRID)
        self.assertIsNotNone(result['benchmark_context'])
        self.assertEqual(result['benchmark_context']['source'], 'category_similarity')
        self.assertGreater(result['benchmark_context']['similarity_score'], Decimal('0.00'))
        self.assertIn('historical_benchmark', {factor['factor_name'] for factor in result['factors']})




class ValuationImportFlowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.manager = user_model.objects.create_user(
            username='manager_import_v2',
            password='DemoPass123!',
            role='manager',
        )
        self.analyst = user_model.objects.create_user(
            username='analyst_import_v2',
            password='DemoPass123!',
            role='analyst',
        )
        self.visitor = user_model.objects.create_user(
            username='visitor_import_v2',
            password='DemoPass123!',
            role='visitor',
        )
        self.creditor = Creditor.objects.create(name='Import Creditor', category=Creditor.Category.FINTECH)

    def _csv_file(self, name='valuation_upload.csv'):
        content = (
            'external_id,full_name,days_past_due,outstanding_principal,outstanding_total,phone_number,status\n'
            'NEW-001,Import Debtor One,120,1400.00,1650.00,0888000011,new\n'
            'NEW-002,Import Debtor Two,45,650.00,760.00,,promise_to_pay\n'
        )
        return SimpleUploadedFile(name, content.encode('utf-8'), content_type='text/csv')

    def test_manager_can_preview_and_confirm_valuation_import(self):
        self.client.login(username='manager_import_v2', password='DemoPass123!')

        preview_response = self.client.post(
            reverse('valuation-import'),
            {
                'action': 'preview',
                'portfolio_name': 'Imported V2 Portfolio',
                'source_company': 'Acquisition Source',
                'purchase_date': '2026-03-11',
                'purchase_price': '15000.00',
                'face_value': '92000.00',
                'currency': 'EUR',
                'existing_creditor': self.creditor.id,
                'creditor_name': '',
                'creditor_category': '',
                'data_file': self._csv_file(),
            },
        )

        self.assertEqual(preview_response.status_code, 200)
        self.assertContains(preview_response, 'Import Readiness')
        self.assertContains(preview_response, 'Import Creditor')

        confirm_response = self.client.post(reverse('valuation-import'), {'action': 'confirm'}, follow=True)
        self.assertEqual(confirm_response.status_code, 200)
        self.assertContains(confirm_response, 'Valuation import completed for Imported V2 Portfolio')
        self.assertTrue(Portfolio.objects.filter(name='Imported V2 Portfolio').exists())
        portfolio = Portfolio.objects.get(name='Imported V2 Portfolio')
        self.assertEqual(portfolio.debtors.count(), 2)
        self.assertTrue(PortfolioUploadBatch.objects.filter(portfolio=portfolio, creditor=self.creditor).exists())
        self.assertContains(confirm_response, 'Valuation Visual Analytics')

    def test_visitor_receives_friendly_access_page_for_import(self):
        self.client.login(username='visitor_import_v2', password='DemoPass123!')
        response = self.client.get(reverse('valuation-import'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'view-only')

    def test_analyst_receives_friendly_access_page_for_import(self):
        self.client.login(username='analyst_import_v2', password='DemoPass123!')
        response = self.client.get(reverse('valuation-import'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Access Restricted')
        self.assertContains(response, 'Manager or Admin')


class BenchmarkManagementViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.manager = user_model.objects.create_user(
            username='manager_bench_v2',
            password='DemoPass123!',
            role='manager',
        )
        self.analyst = user_model.objects.create_user(
            username='analyst_bench_v2',
            password='DemoPass123!',
            role='analyst',
        )
        self.visitor = user_model.objects.create_user(
            username='visitor_bench_v2',
            password='DemoPass123!',
            role='visitor',
        )
        self.creditor = Creditor.objects.create(name='Benchmark Creditor', category=Creditor.Category.BANK)
        self.benchmark = HistoricalBenchmark.objects.create(
            creditor=self.creditor,
            creditor_category=Creditor.Category.BANK,
            product_type='Consumer Loan',
            dpd_band='90-179 days',
            balance_band='2000-4999',
            region='Sofia',
            avg_recovery_rate=Decimal('38.00'),
            avg_contact_rate=Decimal('61.00'),
            avg_ptp_rate=Decimal('19.00'),
            avg_conversion_rate=Decimal('13.00'),
            sample_size=180,
        )

    def test_manager_can_open_benchmark_library(self):
        self.client.login(username='manager_bench_v2', password='DemoPass123!')
        response = self.client.get(reverse('valuation-benchmarks'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Historical Benchmarks')
        self.assertContains(response, 'Benchmark Library')
        self.assertContains(response, 'Benchmark Creditor')

    def test_manager_can_create_benchmark(self):
        self.client.login(username='manager_bench_v2', password='DemoPass123!')
        response = self.client.post(
            reverse('valuation-benchmarks'),
            {
                'creditor': self.creditor.id,
                'creditor_category': Creditor.Category.BANK,
                'product_type': 'SME Loan',
                'dpd_band': '180+ days',
                'balance_band': '5000+',
                'region': 'Plovdiv',
                'avg_recovery_rate': '29.00',
                'avg_contact_rate': '47.00',
                'avg_ptp_rate': '14.00',
                'avg_conversion_rate': '9.00',
                'sample_size': '95',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Benchmark saved')
        self.assertTrue(HistoricalBenchmark.objects.filter(product_type='SME Loan').exists())

    def test_manager_can_edit_benchmark(self):
        self.client.login(username='manager_bench_v2', password='DemoPass123!')
        response = self.client.post(
            reverse('valuation-benchmark-edit', args=[self.benchmark.id]),
            {
                'creditor': self.creditor.id,
                'creditor_category': Creditor.Category.BANK,
                'product_type': 'Consumer Loan',
                'dpd_band': '90-179 days',
                'balance_band': '2000-4999',
                'region': 'Sofia',
                'avg_recovery_rate': '41.00',
                'avg_contact_rate': '63.00',
                'avg_ptp_rate': '20.00',
                'avg_conversion_rate': '15.00',
                'sample_size': '200',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Benchmark updated')
        self.benchmark.refresh_from_db()
        self.assertEqual(self.benchmark.avg_recovery_rate, Decimal('41.00'))
        self.assertEqual(self.benchmark.sample_size, 200)

    def test_visitor_can_open_read_only_benchmark_library(self):
        self.client.login(username='visitor_bench_v2', password='DemoPass123!')
        response = self.client.get(reverse('valuation-benchmarks'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Read-Only Benchmark Review')
        self.assertContains(response, 'Read only')

    def test_analyst_receives_friendly_access_page(self):
        self.client.login(username='analyst_bench_v2', password='DemoPass123!')
        response = self.client.get(reverse('valuation-benchmarks'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Access Restricted')
        self.assertContains(response, 'Manager or Admin')


class ValuationWorkspaceViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.manager = user_model.objects.create_user(
            username='manager_v2',
            password='DemoPass123!',
            role='manager',
        )
        self.analyst = user_model.objects.create_user(
            username='analyst_v2',
            password='DemoPass123!',
            role='analyst',
        )
        self.visitor = user_model.objects.create_user(
            username='visitor_v2',
            password='DemoPass123!',
            role='visitor',
        )
        self.portfolio = Portfolio.objects.create(
            name='Workspace Portfolio',
            source_company='Collections Demo',
            purchase_date=date(2026, 3, 11),
            purchase_price=Decimal('15000.00'),
            face_value=Decimal('90000.00'),
            currency='EUR',
            created_by=self.manager,
        )
        self.second_portfolio = Portfolio.objects.create(
            name='Second Workspace Portfolio',
            source_company='Telecom Demo',
            purchase_date=date(2026, 3, 10),
            purchase_price=Decimal('12000.00'),
            face_value=Decimal('70000.00'),
            currency='EUR',
            created_by=self.manager,
        )
        self.third_portfolio = Portfolio.objects.create(
            name='Third Workspace Portfolio',
            source_company='Utilities Demo',
            purchase_date=date(2026, 3, 9),
            purchase_price=Decimal('18000.00'),
            face_value=Decimal('150000.00'),
            currency='EUR',
            created_by=self.manager,
        )
        debtor = Debtor.objects.create(
            portfolio=self.portfolio,
            external_id='WS-001',
            full_name='Workspace Debtor',
            status='paying',
            days_past_due=44,
            outstanding_principal=Decimal('850.00'),
            outstanding_total=Decimal('990.00'),
            risk_score=35,
            risk_band='low',
            phone_number='0888111111',
            email='workspace@example.com',
        )
        Payment.objects.create(
            debtor=debtor,
            paid_amount=Decimal('110.00'),
            payment_date=date(2026, 3, 10),
            channel='bank_transfer',
        )
        Debtor.objects.create(
            portfolio=self.second_portfolio,
            external_id='WS-002',
            full_name='Second Debtor',
            status='new',
            days_past_due=210,
            outstanding_principal=Decimal('2600.00'),
            outstanding_total=Decimal('3010.00'),
            risk_score=82,
            risk_band='high',
        )
        Debtor.objects.create(
            portfolio=self.third_portfolio,
            external_id='WS-003',
            full_name='Third Debtor One',
            status='contacted',
            days_past_due=115,
            outstanding_principal=Decimal('4200.00'),
            outstanding_total=Decimal('4630.00'),
            risk_score=57,
            risk_band='medium',
            email='third@example.com',
        )
        Debtor.objects.create(
            portfolio=self.third_portfolio,
            external_id='WS-004',
            full_name='Third Debtor Two',
            status='promise_to_pay',
            days_past_due=88,
            outstanding_principal=Decimal('1650.00'),
            outstanding_total=Decimal('1900.00'),
            risk_score=49,
            risk_band='medium',
            phone_number='0888333333',
        )
        HistoricalBenchmark.objects.create(
            creditor_category=Creditor.Category.OTHER,
            dpd_band='180+ days',
            balance_band='2000-4999',
            avg_recovery_rate=Decimal('28.00'),
            avg_contact_rate=Decimal('50.00'),
            avg_ptp_rate=Decimal('14.00'),
            avg_conversion_rate=Decimal('10.00'),
            sample_size=120,
        )

    def test_visitor_can_open_workspace(self):
        self.client.login(username='visitor_v2', password='DemoPass123!')
        response = self.client.get(reverse('valuation-workspace'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Valuation Workspace')
        self.assertContains(response, 'Portfolio Ranking')
        self.assertNotContains(response, 'Valuation Import')

    def test_manager_can_open_workspace(self):
        self.client.login(username='manager_v2', password='DemoPass123!')
        response = self.client.get(reverse('valuation-workspace'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Valuation Workspace')
        self.assertContains(response, 'Portfolio Ranking')
        self.assertContains(response, 'Workspace Portfolio')
        self.assertContains(response, 'Second Workspace Portfolio')
        self.assertContains(response, 'Recommendation')
        self.assertTrue(any(label in response.content.decode() for label in ['Bid', 'Hold', 'Reject']))
        self.assertContains(response, 'Open')

    def test_visitor_can_open_read_only_benchmark_library(self):
        self.client.login(username='visitor_v2', password='DemoPass123!')
        response = self.client.get(reverse('valuation-benchmarks'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Read-Only Benchmark Review')
        self.assertContains(response, 'Read only')

    def test_analyst_receives_friendly_access_page(self):
        self.client.login(username='analyst_v2', password='DemoPass123!')
        response = self.client.get(reverse('valuation-workspace'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Access Restricted')
        self.assertContains(response, 'Manager or Admin')

    def test_manager_can_filter_workspace_by_recommendation(self):
        self.client.login(username='manager_v2', password='DemoPass123!')
        response = self.client.get(reverse('valuation-workspace'), {'recommendation': 'Reject'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'portfolios match the current review filters')
        cards = response.context['portfolio_cards']
        self.assertTrue(cards)
        self.assertTrue(all(item['recommended_action']['label'] == 'Reject' for item in cards))

    def test_manager_can_filter_workspace_by_mode(self):
        self.client.login(username='manager_v2', password='DemoPass123!')
        response = self.client.get(reverse('valuation-workspace'), {'mode': 'Hybrid'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hybrid')
        cards = response.context['portfolio_cards']
        self.assertTrue(cards)
        self.assertTrue(all(item['mode_label'] == 'Hybrid' for item in cards))

    def test_manager_can_sort_workspace_by_face_value(self):
        self.client.login(username='manager_v2', password='DemoPass123!')
        response = self.client.get(reverse('valuation-workspace'), {'sort': 'face_value_desc'})

        self.assertEqual(response.status_code, 200)
        cards = response.context['portfolio_cards']
        self.assertEqual(cards[0]['portfolio'].name, 'Third Workspace Portfolio')
        self.assertEqual(response.context['selected_sort'], 'face_value_desc')

    def test_manager_can_open_comparison_desk(self):
        self.client.login(username='manager_v2', password='DemoPass123!')
        response = self.client.get(
            reverse('valuation-compare'),
            {'portfolio': [self.portfolio.id, self.second_portfolio.id, self.third_portfolio.id]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Portfolio Comparison Desk')
        self.assertContains(response, 'Side-by-Side Comparison')
        self.assertContains(response, 'Lead vs Challenger Delta')
        self.assertContains(response, 'Third Workspace Portfolio')

    def test_visitor_can_open_comparison_desk(self):
        self.client.login(username='visitor_v2', password='DemoPass123!')
        response = self.client.get(
            reverse('valuation-compare'),
            {'portfolio': [self.portfolio.id, self.second_portfolio.id]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Portfolio Comparison Desk')

    def test_analyst_receives_friendly_access_page_for_comparison_desk(self):
        self.client.login(username='analyst_v2', password='DemoPass123!')
        response = self.client.get(reverse('valuation-compare'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Access Restricted')
        self.assertContains(response, 'Manager or Admin')

    def test_visitor_can_open_preview_but_not_run_saved_valuation(self):
        self.client.login(username='visitor_v2', password='DemoPass123!')

        preview_response = self.client.get(reverse('valuation-preview', args=[self.portfolio.id]))
        self.assertEqual(preview_response.status_code, 200)
        self.assertContains(preview_response, 'Open Valuation Report')
        self.assertNotContains(preview_response, 'Run and Save Valuation')

        post_response = self.client.post(reverse('valuation-run', args=[self.portfolio.id]), follow=True)
        self.assertEqual(post_response.status_code, 200)
        self.assertContains(post_response, 'view-only')

    def test_manager_can_open_preview_and_run_saved_valuation(self):
        self.client.login(username='manager_v2', password='DemoPass123!')

        preview_response = self.client.get(reverse('valuation-preview', args=[self.portfolio.id]))
        self.assertEqual(preview_response.status_code, 200)
        self.assertContains(preview_response, 'Run and Save Valuation')
        self.assertContains(preview_response, 'Valuation Visual Analytics')
        self.assertContains(preview_response, 'Portfolio Signals')
        self.assertContains(preview_response, 'Scenario Analysis')
        self.assertContains(preview_response, 'Scenario ROI Ladder')
        self.assertContains(preview_response, 'Recommended Action')
        self.assertContains(preview_response, 'ML Baseline Forecast')
        self.assertContains(preview_response, 'Baseline Recovery Model')
        self.assertContains(preview_response, 'ML-Ready Feature Snapshot')
        self.assertContains(preview_response, 'Collection Efficiency')

        post_response = self.client.post(reverse('valuation-run', args=[self.portfolio.id]), follow=True)
        self.assertEqual(post_response.status_code, 200)
        self.assertContains(post_response, 'Rule-based valuation saved')
        self.assertEqual(PortfolioValuation.objects.filter(portfolio=self.portfolio).count(), 1)
        self.assertGreater(
            ValuationFactor.objects.filter(valuation__portfolio=self.portfolio).count(),
            0,
        )

        self.client.post(reverse('valuation-run', args=[self.portfolio.id]), follow=True)
        comparison_response = self.client.get(reverse('valuation-preview', args=[self.portfolio.id]))
        self.assertEqual(comparison_response.status_code, 200)
        self.assertContains(comparison_response, 'Saved Run Comparison')
        self.assertContains(comparison_response, 'Baseline')
        self.assertEqual(PortfolioValuation.objects.filter(portfolio=self.portfolio).count(), 2)

    def test_manager_can_open_and_export_valuation_report(self):
        self.client.login(username='manager_v2', password='DemoPass123!')
        self.client.post(reverse('valuation-run', args=[self.portfolio.id]), follow=True)

        preview_response = self.client.get(reverse('valuation-report-preview', args=[self.portfolio.id]))
        self.assertEqual(preview_response.status_code, 200)
        self.assertContains(preview_response, 'Valuation Report')
        self.assertContains(preview_response, 'Download Excel')
        self.assertContains(preview_response, 'Scenario Analysis')
        self.assertContains(preview_response, 'ML Baseline Forecast')
        self.assertContains(preview_response, 'ML-Ready Feature Snapshot')

        excel_response = self.client.get(reverse('valuation-report-excel', args=[self.portfolio.id]))
        self.assertEqual(excel_response.status_code, 200)
        self.assertEqual(
            excel_response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

        pdf_response = self.client.get(reverse('valuation-report-pdf', args=[self.portfolio.id]))
        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(pdf_response['Content-Type'], 'application/pdf')

        self.assertEqual(
            GeneratedReport.objects.filter(report_type=GeneratedReport.ReportType.VALUATION_MEMO).count(),
            2,
        )

    def test_visitor_can_open_report_preview_but_not_export(self):
        self.client.login(username='visitor_v2', password='DemoPass123!')
        response = self.client.get(reverse('valuation-report-preview', args=[self.portfolio.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Valuation Report')
        self.assertNotContains(response, 'Download Excel')

        excel_response = self.client.get(reverse('valuation-report-excel', args=[self.portfolio.id]))
        self.assertEqual(excel_response.status_code, 200)
        self.assertContains(excel_response, 'view-only')

    def test_analyst_receives_friendly_access_page_for_valuation_report(self):
        self.client.login(username='analyst_v2', password='DemoPass123!')
        response = self.client.get(reverse('valuation-report-preview', args=[self.portfolio.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Access Restricted')
        self.assertContains(response, 'Manager or Admin')


