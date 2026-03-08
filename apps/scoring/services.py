from decimal import Decimal


def _to_decimal(value):
    return Decimal(str(value))


def _risk_band_from_score(score):
    if score >= 70:
        return 'high'
    if score >= 40:
        return 'medium'
    return 'low'


def calculate_risk_profile(*, days_past_due, outstanding_total, status):
    """Return risk profile based on rule-based weighted factors."""
    score = 0
    reasons = []

    days = int(days_past_due)
    total = _to_decimal(outstanding_total)
    normalized_status = (status or 'new').strip().lower()

    if days >= 180:
        score += 45
        reasons.append('days_past_due >= 180 (+45)')
    elif days >= 90:
        score += 30
        reasons.append('days_past_due >= 90 (+30)')
    elif days >= 30:
        score += 15
        reasons.append('days_past_due >= 30 (+15)')

    if total >= Decimal('5000'):
        score += 30
        reasons.append('outstanding_total >= 5000 (+30)')
    elif total >= Decimal('1000'):
        score += 20
        reasons.append('outstanding_total >= 1000 (+20)')
    elif total >= Decimal('300'):
        score += 10
        reasons.append('outstanding_total >= 300 (+10)')

    status_weights = {
        'new': 10,
        'contacted': 5,
        'promise_to_pay': 0,
        'paying': -10,
        'closed': -20,
    }
    status_weight = status_weights.get(normalized_status, 5)
    score += status_weight
    reasons.append(f'status={normalized_status} ({status_weight:+d})')

    bounded_score = max(0, min(score, 100))

    return {
        'risk_score': bounded_score,
        'risk_band': _risk_band_from_score(bounded_score),
        'reason_factors': reasons,
    }
