from decimal import Decimal, ROUND_HALF_UP

from django.db.models import DecimalField, Max, Sum, Value
from django.db.models.functions import Coalesce

ZERO_DECIMAL = Value(Decimal('0.00'), output_field=DecimalField(max_digits=14, decimal_places=2))


def _round_metric(value):
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _safe_ratio(numerator, denominator):
    if not denominator:
        return Decimal('0.00')
    return Decimal(numerator) / Decimal(denominator)


def build_feature_snapshot(*, portfolio, debtors, payments, total_debtors, outstanding_total, collected_total, avg_days_past_due, high_risk_share, medium_risk_share, low_risk_share, contactability_share, ptp_share, paying_share, closed_share):
    phone_coverage = _safe_ratio(debtors.exclude(phone_number='').count(), total_debtors)
    email_coverage = _safe_ratio(debtors.exclude(email='').count(), total_debtors)
    region_rows = list(
        debtors.exclude(region='')
        .values('region')
        .annotate(total=Sum(Value(1)))
        .order_by('-total')
    )
    top_region_share = Decimal('0.00')
    dominant_region = 'All regions'
    if region_rows:
        dominant_region = region_rows[0]['region']
        top_region_share = _safe_ratio(region_rows[0]['total'], total_debtors)

    avg_balance = _safe_ratio(outstanding_total, total_debtors)
    avg_principal = debtors.aggregate(value=Coalesce(Sum('outstanding_principal'), ZERO_DECIMAL))['value']
    avg_principal = _safe_ratio(avg_principal, total_debtors)
    max_days_past_due = debtors.aggregate(value=Coalesce(Max('days_past_due'), Value(0)))['value']
    face_value = Decimal(portfolio.face_value)
    purchase_price = Decimal(portfolio.purchase_price)

    leverage_ratio = _safe_ratio(purchase_price, face_value)
    outstanding_to_face = _safe_ratio(outstanding_total, face_value)
    collected_to_outstanding = _safe_ratio(collected_total, outstanding_total)
    balance_to_face_per_debtor = _safe_ratio(avg_balance, face_value)
    principal_to_total = _safe_ratio(avg_principal, avg_balance) if avg_balance else Decimal('0.00')

    feature_vector = {
        'debtor_count': total_debtors,
        'avg_balance': _round_metric(avg_balance),
        'avg_principal': _round_metric(avg_principal),
        'avg_days_past_due': _round_metric(avg_days_past_due),
        'max_days_past_due': int(max_days_past_due),
        'high_risk_share': _round_metric(high_risk_share * Decimal('100')),
        'medium_risk_share': _round_metric(medium_risk_share * Decimal('100')),
        'low_risk_share': _round_metric(low_risk_share * Decimal('100')),
        'contactability_share': _round_metric(contactability_share * Decimal('100')),
        'phone_coverage': _round_metric(phone_coverage * Decimal('100')),
        'email_coverage': _round_metric(email_coverage * Decimal('100')),
        'ptp_share': _round_metric(ptp_share * Decimal('100')),
        'paying_share': _round_metric(paying_share * Decimal('100')),
        'closed_share': _round_metric(closed_share * Decimal('100')),
        'top_region_share': _round_metric(top_region_share * Decimal('100')),
        'purchase_price_pct_of_face': _round_metric(leverage_ratio * Decimal('100')),
        'outstanding_to_face_pct': _round_metric(outstanding_to_face * Decimal('100')),
        'collection_efficiency_pct': _round_metric(collected_to_outstanding * Decimal('100')),
        'balance_to_face_per_debtor_pct': _round_metric(balance_to_face_per_debtor * Decimal('100')),
        'principal_to_total_pct': _round_metric(principal_to_total * Decimal('100')),
    }

    feature_groups = [
        {
            'title': 'Portfolio Structure',
            'items': [
                {'label': 'Debtor Count', 'value': feature_vector['debtor_count']},
                {'label': 'Avg Balance', 'value': feature_vector['avg_balance']},
                {'label': 'Avg Principal', 'value': feature_vector['avg_principal']},
                {'label': 'Outstanding / Face', 'value': f"{feature_vector['outstanding_to_face_pct']}%"},
                {'label': 'Purchase / Face', 'value': f"{feature_vector['purchase_price_pct_of_face']}%"},
            ],
        },
        {
            'title': 'Risk & Aging',
            'items': [
                {'label': 'Avg DPD', 'value': feature_vector['avg_days_past_due']},
                {'label': 'Max DPD', 'value': feature_vector['max_days_past_due']},
                {'label': 'High Risk Share', 'value': f"{feature_vector['high_risk_share']}%"},
                {'label': 'Medium Risk Share', 'value': f"{feature_vector['medium_risk_share']}%"},
                {'label': 'Low Risk Share', 'value': f"{feature_vector['low_risk_share']}%"},
            ],
        },
        {
            'title': 'Collections Signals',
            'items': [
                {'label': 'Contactability', 'value': f"{feature_vector['contactability_share']}%"},
                {'label': 'Phone Coverage', 'value': f"{feature_vector['phone_coverage']}%"},
                {'label': 'Email Coverage', 'value': f"{feature_vector['email_coverage']}%"},
                {'label': 'PTP Share', 'value': f"{feature_vector['ptp_share']}%"},
                {'label': 'Paying Share', 'value': f"{feature_vector['paying_share']}%"},
            ],
        },
        {
            'title': 'Calibration Features',
            'items': [
                {'label': 'Collection Efficiency', 'value': f"{feature_vector['collection_efficiency_pct']}%"},
                {'label': 'Principal / Total', 'value': f"{feature_vector['principal_to_total_pct']}%"},
                {'label': 'Balance / Face per Debtor', 'value': f"{feature_vector['balance_to_face_per_debtor_pct']}%"},
                {'label': 'Dominant Region', 'value': dominant_region},
                {'label': 'Top Region Share', 'value': f"{feature_vector['top_region_share']}%"},
            ],
        },
    ]

    return {
        'vector': feature_vector,
        'groups': feature_groups,
        'dominant_region': dominant_region,
    }
