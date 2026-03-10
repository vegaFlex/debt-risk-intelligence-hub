from django.core.management import call_command
from django.test import TestCase

from apps.portfolio.models import Debtor, Portfolio


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
