from decimal import Decimal

from django.test import SimpleTestCase

from apps.portfolio.importers import ImportValidationError, parse_uploaded_file, validate_rows


class DummyUpload:
    def __init__(self, name, text):
        self.name = name
        self._payload = text.encode('utf-8')

    def read(self):
        return self._payload


class PortfolioImportersTests(SimpleTestCase):
    def test_parse_uploaded_file_csv(self):
        upload = DummyUpload(
            'portfolio.csv',
            'external_id,full_name,days_past_due,outstanding_principal,outstanding_total\n'
            'A1,John Doe,45,100.00,120.00\n',
        )
        rows, source_type = parse_uploaded_file(upload)
        self.assertEqual(source_type, 'csv')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['external_id'], 'A1')

    def test_parse_uploaded_file_rejects_non_csv(self):
        upload = DummyUpload('portfolio.xlsx', 'dummy')
        with self.assertRaises(ImportValidationError):
            parse_uploaded_file(upload)

    def test_validate_rows_success(self):
        rows = [
            {
                'external_id': 'A1',
                'full_name': 'John Doe',
                'days_past_due': '30',
                'outstanding_principal': '100.00',
                'outstanding_total': '120.00',
                'status': 'new',
                'risk_band': 'medium',
                'national_id': '',
                'phone_number': '',
                'email': '',
                'region': '',
            }
        ]

        cleaned, errors = validate_rows(rows)

        self.assertEqual(errors, [])
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned[0]['external_id'], 'A1')
        self.assertEqual(cleaned[0]['days_past_due'], 30)
        self.assertEqual(cleaned[0]['outstanding_total'], Decimal('120.00'))

    def test_validate_rows_missing_required_columns(self):
        rows = [{'external_id': 'A1', 'full_name': 'John Doe'}]

        with self.assertRaises(ImportValidationError):
            validate_rows(rows)

    def test_validate_rows_collects_row_errors(self):
        rows = [
            {
                'external_id': 'A1',
                'full_name': '',
                'days_past_due': '30',
                'outstanding_principal': '100.00',
                'outstanding_total': '120.00',
                'status': 'new',
                'risk_band': 'medium',
                'national_id': '',
                'phone_number': '',
                'email': '',
                'region': '',
            },
            {
                'external_id': 'A1',
                'full_name': 'Dup Name',
                'days_past_due': '30',
                'outstanding_principal': '100.00',
                'outstanding_total': '120.00',
                'status': 'new',
                'risk_band': 'medium',
                'national_id': '',
                'phone_number': '',
                'email': '',
                'region': '',
            },
        ]

        cleaned, errors = validate_rows(rows)

        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned[0]['external_id'], 'A1')
        self.assertEqual(len(errors), 1)

