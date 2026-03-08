from django.test import TestCase

from apps.scoring.services import calculate_risk_profile


class RiskScoringServiceTests(TestCase):
    def test_high_risk_profile(self):
        result = calculate_risk_profile(
            days_past_due=220,
            outstanding_total='6400',
            status='new',
        )

        self.assertEqual(result['risk_band'], 'high')
        self.assertGreaterEqual(result['risk_score'], 70)
        self.assertTrue(result['reason_factors'])

    def test_low_risk_profile(self):
        result = calculate_risk_profile(
            days_past_due=5,
            outstanding_total='120',
            status='closed',
        )

        self.assertEqual(result['risk_band'], 'low')
        self.assertLess(result['risk_score'], 40)

    def test_medium_risk_profile(self):
        result = calculate_risk_profile(
            days_past_due=45,
            outstanding_total='1200',
            status='contacted',
        )

        self.assertEqual(result['risk_band'], 'medium')
        self.assertGreaterEqual(result['risk_score'], 40)
        self.assertLess(result['risk_score'], 70)
