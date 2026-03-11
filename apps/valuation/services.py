from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Count, DecimalField, Sum, Value
from django.db.models.functions import Coalesce

from apps.portfolio.models import Debtor, Payment, Portfolio
from apps.valuation.models import PortfolioValuation, ValuationFactor

ZERO_DECIMAL = Value(Decimal('0.00'), output_field=DecimalField(max_digits=14, decimal_places=2))


def _round_money(value):
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _round_metric(value):
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _factor(name, weight, value, explanation):
    return {
        'factor_name': name,
        'factor_weight': _round_metric(weight),
        'factor_value': value,
        'explanation': explanation,
    }


def _debtor_queryset(portfolio):
    return Debtor.objects.filter(portfolio=portfolio)


def _payment_queryset(portfolio):
    return Payment.objects.filter(debtor__portfolio=portfolio)


def build_rule_based_valuation(portfolio):
    debtors = _debtor_queryset(portfolio)
    payments = _payment_queryset(portfolio)

    total_debtors = debtors.count()
    if total_debtors == 0:
        return {
            'portfolio': portfolio,
            'face_value': _round_money(portfolio.face_value),
            'expected_recovery_rate': Decimal('0.00'),
            'expected_collections': Decimal('0.00'),
            'recommended_bid_pct': Decimal('0.00'),
            'recommended_bid_amount': Decimal('0.00'),
            'projected_roi': Decimal('0.00'),
            'confidence_score': Decimal('0.00'),
            'factors': [
                _factor(
                    'empty_portfolio',
                    Decimal('0.00'),
                    '0 debtors',
                    'No debtors are available, so the portfolio cannot be valued yet.',
                )
            ],
            'stats': {
                'total_debtors': 0,
                'outstanding_total': Decimal('0.00'),
                'collected_total': Decimal('0.00'),
                'high_risk_share': Decimal('0.00'),
                'contactability_share': Decimal('0.00'),
                'ptp_share': Decimal('0.00'),
                'paying_share': Decimal('0.00'),
                'median_days_past_due_proxy': Decimal('0.00'),
            },
        }

    outstanding_total = debtors.aggregate(value=Coalesce(Sum('outstanding_total'), ZERO_DECIMAL))['value']
    collected_total = payments.aggregate(value=Coalesce(Sum('paid_amount'), ZERO_DECIMAL))['value']

    high_risk_count = debtors.filter(risk_band='high').count()
    medium_risk_count = debtors.filter(risk_band='medium').count()
    low_risk_count = debtors.filter(risk_band='low').count()

    reachable_count = debtors.exclude(phone_number='').count() + debtors.exclude(email='').count()
    reachable_count = min(total_debtors, reachable_count)

    promise_count = debtors.filter(status='promise_to_pay').count()
    paying_count = debtors.filter(status='paying').count()
    closed_count = debtors.filter(status='closed').count()

    avg_days_past_due = debtors.aggregate(value=Coalesce(Sum('days_past_due'), Value(0)))['value'] / total_debtors

    high_risk_share = Decimal(high_risk_count) / Decimal(total_debtors)
    medium_risk_share = Decimal(medium_risk_count) / Decimal(total_debtors)
    low_risk_share = Decimal(low_risk_count) / Decimal(total_debtors)
    contactability_share = Decimal(reachable_count) / Decimal(total_debtors)
    ptp_share = Decimal(promise_count) / Decimal(total_debtors)
    paying_share = Decimal(paying_count) / Decimal(total_debtors)
    closed_share = Decimal(closed_count) / Decimal(total_debtors)

    recovery_score = Decimal('0.18')
    factors = []

    low_risk_boost = low_risk_share * Decimal('0.22')
    recovery_score += low_risk_boost
    factors.append(
        _factor(
            'low_risk_mix',
            low_risk_boost * Decimal('100'),
            f'{(low_risk_share * Decimal("100")).quantize(Decimal("0.01"))}%',
            'A larger low-risk share improves expected recoverability.',
        )
    )

    medium_risk_boost = medium_risk_share * Decimal('0.08')
    recovery_score += medium_risk_boost
    factors.append(
        _factor(
            'medium_risk_mix',
            medium_risk_boost * Decimal('100'),
            f'{(medium_risk_share * Decimal("100")).quantize(Decimal("0.01"))}%',
            'Medium-risk debtors contribute moderate recovery potential.',
        )
    )

    high_risk_penalty = high_risk_share * Decimal('0.17')
    recovery_score -= high_risk_penalty
    factors.append(
        _factor(
            'high_risk_concentration',
            -(high_risk_penalty * Decimal('100')),
            f'{(high_risk_share * Decimal("100")).quantize(Decimal("0.01"))}%',
            'High-risk concentration reduces expected recovery performance.',
        )
    )

    contactability_boost = contactability_share * Decimal('0.16')
    recovery_score += contactability_boost
    factors.append(
        _factor(
            'contactability',
            contactability_boost * Decimal('100'),
            f'{(contactability_share * Decimal("100")).quantize(Decimal("0.01"))}%',
            'Reachable debtors improve operational recovery odds.',
        )
    )

    ptp_boost = ptp_share * Decimal('0.14')
    recovery_score += ptp_boost
    factors.append(
        _factor(
            'promise_to_pay_share',
            ptp_boost * Decimal('100'),
            f'{(ptp_share * Decimal("100")).quantize(Decimal("0.01"))}%',
            'Promise-to-pay cases improve near-term collection expectations.',
        )
    )

    paying_boost = paying_share * Decimal('0.18')
    recovery_score += paying_boost
    factors.append(
        _factor(
            'paying_share',
            paying_boost * Decimal('100'),
            f'{(paying_share * Decimal("100")).quantize(Decimal("0.01"))}%',
            'Active paying debtors improve projected realized collections.',
        )
    )

    closed_boost = closed_share * Decimal('0.05')
    recovery_score += closed_boost
    factors.append(
        _factor(
            'closed_share',
            closed_boost * Decimal('100'),
            f'{(closed_share * Decimal("100")).quantize(Decimal("0.01"))}%',
            'Closed cases indicate some historical resolution capacity in the portfolio.',
        )
    )

    if avg_days_past_due >= 180:
        days_penalty = Decimal('0.08')
        label = '180+ days'
    elif avg_days_past_due >= 90:
        days_penalty = Decimal('0.04')
        label = '90+ days'
    elif avg_days_past_due >= 30:
        days_penalty = Decimal('0.02')
        label = '30+ days'
    else:
        days_penalty = Decimal('-0.01')
        label = 'under 30 days'

    recovery_score -= days_penalty
    factors.append(
        _factor(
            'aging_profile',
            -(days_penalty * Decimal('100')),
            label,
            'Older delinquency generally reduces recoverability and bid appetite.',
        )
    )

    bounded_recovery_rate = max(Decimal('0.05'), min(recovery_score, Decimal('0.75')))
    expected_collections = _round_money(outstanding_total * bounded_recovery_rate)

    bid_pct = bounded_recovery_rate * Decimal('0.42')
    if contactability_share >= Decimal('0.70'):
        bid_pct += Decimal('0.015')
    if high_risk_share >= Decimal('0.50'):
        bid_pct -= Decimal('0.02')
    if paying_share >= Decimal('0.15'):
        bid_pct += Decimal('0.01')

    recommended_bid_pct = max(Decimal('0.03'), min(bid_pct, Decimal('0.25')))
    recommended_bid_amount = _round_money(Decimal(portfolio.face_value) * recommended_bid_pct)

    if recommended_bid_amount > 0:
        projected_roi = ((expected_collections - recommended_bid_amount) / recommended_bid_amount) * Decimal('100')
    else:
        projected_roi = Decimal('0.00')

    collected_ratio = (Decimal(collected_total) / Decimal(outstanding_total)) if outstanding_total else Decimal('0.00')
    confidence_score = Decimal('42.0')
    confidence_score += contactability_share * Decimal('18')
    confidence_score += min(ptp_share * Decimal('25'), Decimal('12'))
    confidence_score += min(paying_share * Decimal('30'), Decimal('14'))
    confidence_score += min(collected_ratio * Decimal('60'), Decimal('14'))
    confidence_score -= min(high_risk_share * Decimal('18'), Decimal('12'))
    confidence_score = max(Decimal('15.0'), min(confidence_score, Decimal('95.0')))

    return {
        'portfolio': portfolio,
        'face_value': _round_money(portfolio.face_value),
        'expected_recovery_rate': _round_metric(bounded_recovery_rate * Decimal('100')),
        'expected_collections': expected_collections,
        'recommended_bid_pct': _round_metric(recommended_bid_pct * Decimal('100')),
        'recommended_bid_amount': recommended_bid_amount,
        'projected_roi': _round_metric(projected_roi),
        'confidence_score': _round_metric(confidence_score),
        'factors': factors,
        'stats': {
            'total_debtors': total_debtors,
            'outstanding_total': _round_money(outstanding_total),
            'collected_total': _round_money(collected_total),
            'high_risk_share': _round_metric(high_risk_share * Decimal('100')),
            'contactability_share': _round_metric(contactability_share * Decimal('100')),
            'ptp_share': _round_metric(ptp_share * Decimal('100')),
            'paying_share': _round_metric(paying_share * Decimal('100')),
            'median_days_past_due_proxy': _round_metric(avg_days_past_due),
        },
    }


def persist_rule_based_valuation(portfolio, *, creditor=None, upload_batch=None, created_by=None):
    valuation_data = build_rule_based_valuation(portfolio)
    valuation = PortfolioValuation.objects.create(
        portfolio=portfolio,
        creditor=creditor,
        upload_batch=upload_batch,
        face_value=valuation_data['face_value'],
        expected_recovery_rate=valuation_data['expected_recovery_rate'],
        expected_collections=valuation_data['expected_collections'],
        recommended_bid_pct=valuation_data['recommended_bid_pct'],
        recommended_bid_amount=valuation_data['recommended_bid_amount'],
        projected_roi=valuation_data['projected_roi'],
        confidence_score=valuation_data['confidence_score'],
        valuation_method=PortfolioValuation.ValuationMethod.RULE_BASED,
        created_by=created_by,
    )

    ValuationFactor.objects.bulk_create(
        [
            ValuationFactor(
                valuation=valuation,
                factor_name=factor['factor_name'],
                factor_weight=factor['factor_weight'],
                factor_value=factor['factor_value'],
                explanation=factor['explanation'],
            )
            for factor in valuation_data['factors']
        ]
    )

    return valuation
