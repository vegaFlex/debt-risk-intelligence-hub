from django.core.management import call_command
from django.test import TestCase

from apps.portfolio.models import Debtor, Portfolio
from apps.valuation.models import Creditor, HistoricalBenchmark, PortfolioUploadBatch


class SeedDemoDataCommandTests(TestCase):
    def test_seed_demo_data_creates_bulk_demo_packages(self):
        call_command('seed_demo_data')

        self.assertEqual(Portfolio.objects.count(), 6)
        self.assertEqual(Debtor.objects.count(), 2505)
        self.assertEqual(Portfolio.objects.filter(name__startswith='Retail Recovery Pack').count(), 1)
        self.assertEqual(Portfolio.objects.filter(name__startswith='Consumer Debt Pack').count(), 1)
        self.assertEqual(Portfolio.objects.filter(name__startswith='SME Collections Pack').count(), 1)
        self.assertEqual(Portfolio.objects.filter(name__startswith='Telecom Arrears Pack').count(), 1)
        self.assertEqual(Portfolio.objects.filter(name__startswith='Utilities Debt Pack').count(), 1)
        self.assertEqual(Portfolio.objects.exclude(currency='EUR').count(), 0)
        self.assertEqual(Creditor.objects.count(), 6)
        self.assertEqual(HistoricalBenchmark.objects.count(), 7)
        self.assertEqual(PortfolioUploadBatch.objects.count(), 6)
        self.assertEqual(PortfolioUploadBatch.objects.filter(creditor__isnull=False).count(), 6)
