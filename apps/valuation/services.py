from decimal import Decimal, ROUND_HALF_UP

from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce

from apps.portfolio.models import Debtor, Payment
from apps.valuation.models import HistoricalBenchmark, PortfolioValuation, ValuationFactor

ZERO_DECIMAL = Value(Decimal('0.00'), output_field=DecimalField(max_digits=14, decimal_places=2))
SCENARIO_BID_PCTS = (
    Decimal('6.00'),
    Decimal('8.00'),
    Decimal('10.00'),
    Decimal('12.00'),
)


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


def _portfolio_creditor(portfolio, creditor=None):
    if creditor:
        return creditor
    batch = getattr(portfolio, 'valuation_batch', None)
    return getattr(batch, 'creditor', None)


def _dpd_band(avg_days_past_due):
    if avg_days_past_due >= 180:
        return '180+ days'
    if avg_days_past_due >= 90:
        return '90-179 days'
    if avg_days_past_due >= 30:
        return '30-89 days'
    return 'under 30 days'


def _balance_band(outstanding_total, total_debtors):
    average_balance = Decimal(outstanding_total) / Decimal(total_debtors)
    if average_balance >= Decimal('5000'):
        return '5000+'
    if average_balance >= Decimal('2000'):
        return '2000-4999'
    if average_balance >= Decimal('1000'):
        return '1000-1999'
    return 'under 1000'


def _dominant_region(debtors):
    region_rows = [row for row in debtors.exclude(region='').values('region').annotate(total=Sum(Value(1))) if row['region']]
    if not region_rows:
        return ''
    region_rows.sort(key=lambda row: row['total'], reverse=True)
    return region_rows[0]['region']


def _resolve_benchmark(portfolio, *, creditor, avg_days_past_due, outstanding_total, total_debtors, debtors):
    dpd_band = _dpd_band(avg_days_past_due)
    balance_band = _balance_band(outstanding_total, total_debtors)
    region = _dominant_region(debtors)
    creditor_category = getattr(creditor, 'category', None) or HistoricalBenchmark._meta.get_field('creditor_category').default

    queryset = HistoricalBenchmark.objects.filter(dpd_band=dpd_band, balance_band=balance_band)
    if region:
        region_match = queryset.filter(region=region)
        if region_match.exists():
            queryset = region_match
        else:
            queryset = queryset.filter(region='') | queryset.filter(region__isnull=True)

    exact_creditor = queryset.filter(creditor=creditor).order_by('-sample_size', '-avg_recovery_rate') if creditor else HistoricalBenchmark.objects.none()
    if exact_creditor.exists():
        benchmark = exact_creditor.first()
        return benchmark, 'creditor_specific', creditor_category, dpd_band, balance_band, region

    category_match = queryset.filter(creditor__isnull=True, creditor_category=creditor_category).order_by('-sample_size', '-avg_recovery_rate')
    if category_match.exists():
        benchmark = category_match.first()
        return benchmark, 'category_fallback', creditor_category, dpd_band, balance_band, region

    generic_match = queryset.filter(creditor__isnull=True).order_by('-sample_size', '-avg_recovery_rate')
    if generic_match.exists():
        benchmark = generic_match.first()
        return benchmark, 'generic_fallback', creditor_category, dpd_band, balance_band, region

    return None, 'rule_only', creditor_category, dpd_band, balance_band, region


def _build_scenarios(face_value, expected_collections, outstanding_total, recommended_bid_pct):
    scenarios = []
    closest_index = 0
    closest_distance = None

    for index, bid_pct in enumerate(SCENARIO_BID_PCTS):
        bid_amount = _round_money(Decimal(face_value) * (bid_pct / Decimal('100')))
        expected_profit = _round_money(expected_collections - bid_amount)
        roi = Decimal('0.00')
        if bid_amount > 0:
            roi = _round_metric(((expected_collections - bid_amount) / bid_amount) * Decimal('100'))

        break_even_recovery = Decimal('0.00')
        if outstanding_total > 0:
            break_even_recovery = _round_metric((bid_amount / Decimal(outstanding_total)) * Decimal('100'))

        current_bid_pct = _round_metric(bid_pct)
        distance = abs(current_bid_pct - _round_metric(recommended_bid_pct))
        if closest_distance is None or distance < closest_distance:
            closest_distance = distance
            closest_index = index

        scenarios.append(
            {
                'bid_pct': current_bid_pct,
                'bid_amount': bid_amount,
                'expected_profit': expected_profit,
                'roi': roi,
                'break_even_recovery': break_even_recovery,
                'is_recommended': False,
            }
        )

    if scenarios:
        scenarios[closest_index]['is_recommended'] = True

    return scenarios


def _as_percent_decimal(value):
    return _round_metric(Decimal(value) * Decimal('100'))


def _build_visuals(
    *,
    high_risk_share,
    medium_risk_share,
    low_risk_share,
    contactability_share,
    ptp_share,
    paying_share,
    recommended_bid_pct,
    expected_recovery_rate,
    confidence_score,
    scenarios,
):
    risk_mix = [
        {'label': 'High Risk', 'value': _as_percent_decimal(high_risk_share), 'tone': 'danger'},
        {'label': 'Medium Risk', 'value': _as_percent_decimal(medium_risk_share), 'tone': 'warning'},
        {'label': 'Low Risk', 'value': _as_percent_decimal(low_risk_share), 'tone': 'success'},
    ]

    recovery_bridge = [
        {'label': 'Expected Recovery', 'value': _round_metric(expected_recovery_rate), 'tone': 'primary'},
        {'label': 'Bid Threshold', 'value': _round_metric(recommended_bid_pct), 'tone': 'neutral'},
        {'label': 'Confidence', 'value': _round_metric(confidence_score), 'tone': 'success'},
    ]

    operating_signals = [
        {'label': 'Contactability', 'value': _as_percent_decimal(contactability_share), 'tone': 'primary'},
        {'label': 'Promise To Pay', 'value': _as_percent_decimal(ptp_share), 'tone': 'warning'},
        {'label': 'Paying Cases', 'value': _as_percent_decimal(paying_share), 'tone': 'success'},
    ]

    scenario_roi = [
        {
            'label': f"{scenario['bid_pct']}% bid",
            'value': _round_metric(max(Decimal('0.00'), scenario['roi'])),
            'raw_value': scenario['roi'],
            'tone': 'highlight' if scenario['is_recommended'] else 'neutral',
            'is_recommended': scenario['is_recommended'],
        }
        for scenario in scenarios
    ]

    return {
        'risk_mix': risk_mix,
        'recovery_bridge': recovery_bridge,
        'operating_signals': operating_signals,
        'scenario_roi': scenario_roi,
    }


def build_rule_based_valuation(portfolio, *, creditor=None):
    debtors = _debtor_queryset(portfolio)
    payments = _payment_queryset(portfolio)
    creditor = _portfolio_creditor(portfolio, creditor=creditor)

    total_debtors = debtors.count()
    if total_debtors == 0:
        return {
            'portfolio': portfolio,
            'creditor': creditor,
            'face_value': _round_money(portfolio.face_value),
            'expected_recovery_rate': Decimal('0.00'),
            'expected_collections': Decimal('0.00'),
            'recommended_bid_pct': Decimal('0.00'),
            'recommended_bid_amount': Decimal('0.00'),
            'projected_roi': Decimal('0.00'),
            'confidence_score': Decimal('0.00'),
            'valuation_method': PortfolioValuation.ValuationMethod.RULE_BASED,
            'benchmark': None,
            'benchmark_context': None,
            'scenarios': [],
            'visuals': {
                'risk_mix': [],
                'recovery_bridge': [],
                'operating_signals': [],
                'scenario_roi': [],
            },
            'factors': [
                _factor('empty_portfolio', Decimal('0.00'), '0 debtors', 'No debtors are available, so the portfolio cannot be valued yet.')
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
                'dpd_band': 'n/a',
                'balance_band': 'n/a',
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
    factors.append(_factor('low_risk_mix', low_risk_boost * Decimal('100'), f'{(low_risk_share * Decimal("100")).quantize(Decimal("0.01"))}%', 'A larger low-risk share improves expected recoverability.'))

    medium_risk_boost = medium_risk_share * Decimal('0.08')
    recovery_score += medium_risk_boost
    factors.append(_factor('medium_risk_mix', medium_risk_boost * Decimal('100'), f'{(medium_risk_share * Decimal("100")).quantize(Decimal("0.01"))}%', 'Medium-risk debtors contribute moderate recovery potential.'))

    high_risk_penalty = high_risk_share * Decimal('0.17')
    recovery_score -= high_risk_penalty
    factors.append(_factor('high_risk_concentration', -(high_risk_penalty * Decimal('100')), f'{(high_risk_share * Decimal("100")).quantize(Decimal("0.01"))}%', 'High-risk concentration reduces expected recovery performance.'))

    contactability_boost = contactability_share * Decimal('0.16')
    recovery_score += contactability_boost
    factors.append(_factor('contactability', contactability_boost * Decimal('100'), f'{(contactability_share * Decimal("100")).quantize(Decimal("0.01"))}%', 'Reachable debtors improve operational recovery odds.'))

    ptp_boost = ptp_share * Decimal('0.14')
    recovery_score += ptp_boost
    factors.append(_factor('promise_to_pay_share', ptp_boost * Decimal('100'), f'{(ptp_share * Decimal("100")).quantize(Decimal("0.01"))}%', 'Promise-to-pay cases improve near-term collection expectations.'))

    paying_boost = paying_share * Decimal('0.18')
    recovery_score += paying_boost
    factors.append(_factor('paying_share', paying_boost * Decimal('100'), f'{(paying_share * Decimal("100")).quantize(Decimal("0.01"))}%', 'Active paying debtors improve projected realized collections.'))

    closed_boost = closed_share * Decimal('0.05')
    recovery_score += closed_boost
    factors.append(_factor('closed_share', closed_boost * Decimal('100'), f'{(closed_share * Decimal("100")).quantize(Decimal("0.01"))}%', 'Closed cases indicate some historical resolution capacity in the portfolio.'))

    dpd_band = _dpd_band(avg_days_past_due)
    if avg_days_past_due >= 180:
        days_penalty = Decimal('0.08')
    elif avg_days_past_due >= 90:
        days_penalty = Decimal('0.04')
    elif avg_days_past_due >= 30:
        days_penalty = Decimal('0.02')
    else:
        days_penalty = Decimal('-0.01')

    recovery_score -= days_penalty
    factors.append(_factor('aging_profile', -(days_penalty * Decimal('100')), dpd_band, 'Older delinquency generally reduces recoverability and bid appetite.'))

    benchmark, benchmark_source, creditor_category, _, balance_band, region = _resolve_benchmark(
        portfolio,
        creditor=creditor,
        avg_days_past_due=avg_days_past_due,
        outstanding_total=outstanding_total,
        total_debtors=total_debtors,
        debtors=debtors,
    )

    valuation_method = PortfolioValuation.ValuationMethod.RULE_BASED
    if benchmark:
        benchmark_rate = Decimal(benchmark.avg_recovery_rate) / Decimal('100')
        benchmark_weight = Decimal('0.35') if benchmark.sample_size >= 150 else Decimal('0.20')
        recovery_score = (recovery_score * (Decimal('1.00') - benchmark_weight)) + (benchmark_rate * benchmark_weight)
        valuation_method = PortfolioValuation.ValuationMethod.HYBRID
        factors.append(
            _factor(
                'historical_benchmark',
                benchmark_weight * Decimal('100'),
                f'{benchmark.avg_recovery_rate}% from {benchmark_source.replace("_", " ")}',
                'Historical benchmark data blended into the pricing estimate when a comparable segment is available.',
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
    if benchmark and benchmark.sample_size >= 150:
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
    if benchmark:
        confidence_score += Decimal('6.0') if benchmark.sample_size >= 150 else Decimal('3.0')
    confidence_score = max(Decimal('15.0'), min(confidence_score, Decimal('95.0')))

    benchmark_context = None
    if benchmark:
        benchmark_context = {
            'source': benchmark_source,
            'sample_size': benchmark.sample_size,
            'avg_recovery_rate': _round_metric(benchmark.avg_recovery_rate),
            'avg_contact_rate': _round_metric(benchmark.avg_contact_rate),
            'avg_ptp_rate': _round_metric(benchmark.avg_ptp_rate),
            'avg_conversion_rate': _round_metric(benchmark.avg_conversion_rate),
            'creditor_category': creditor_category,
            'dpd_band': benchmark.dpd_band,
            'balance_band': benchmark.balance_band,
            'region': benchmark.region or region or 'All regions',
        }

    scenarios = _build_scenarios(portfolio.face_value, expected_collections, outstanding_total, recommended_bid_pct)
    visuals = _build_visuals(
        high_risk_share=high_risk_share,
        medium_risk_share=medium_risk_share,
        low_risk_share=low_risk_share,
        contactability_share=contactability_share,
        ptp_share=ptp_share,
        paying_share=paying_share,
        recommended_bid_pct=recommended_bid_pct * Decimal('100'),
        expected_recovery_rate=bounded_recovery_rate * Decimal('100'),
        confidence_score=confidence_score,
        scenarios=scenarios,
    )

    return {
        'portfolio': portfolio,
        'creditor': creditor,
        'face_value': _round_money(portfolio.face_value),
        'expected_recovery_rate': _round_metric(bounded_recovery_rate * Decimal('100')),
        'expected_collections': expected_collections,
        'recommended_bid_pct': _round_metric(recommended_bid_pct * Decimal('100')),
        'recommended_bid_amount': recommended_bid_amount,
        'projected_roi': _round_metric(projected_roi),
        'confidence_score': _round_metric(confidence_score),
        'valuation_method': valuation_method,
        'benchmark': benchmark,
        'benchmark_context': benchmark_context,
        'scenarios': scenarios,
        'visuals': visuals,
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
            'dpd_band': dpd_band,
            'balance_band': balance_band,
            'region': region or 'All regions',
        },
    }


def persist_rule_based_valuation(portfolio, *, creditor=None, upload_batch=None, created_by=None):
    valuation_data = build_rule_based_valuation(portfolio, creditor=creditor)
    valuation = PortfolioValuation.objects.create(
        portfolio=portfolio,
        creditor=creditor or valuation_data['creditor'],
        upload_batch=upload_batch,
        face_value=valuation_data['face_value'],
        expected_recovery_rate=valuation_data['expected_recovery_rate'],
        expected_collections=valuation_data['expected_collections'],
        recommended_bid_pct=valuation_data['recommended_bid_pct'],
        recommended_bid_amount=valuation_data['recommended_bid_amount'],
        projected_roi=valuation_data['projected_roi'],
        confidence_score=valuation_data['confidence_score'],
        valuation_method=valuation_data['valuation_method'],
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
