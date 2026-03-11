from django.test import TestCase

from apps.valuation.models import Creditor


class CreditorModelTests(TestCase):
    def test_string_representation_returns_name(self):
        creditor = Creditor.objects.create(name='Test Creditor')

        self.assertEqual(str(creditor), 'Test Creditor')
