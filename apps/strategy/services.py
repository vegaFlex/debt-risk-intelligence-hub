from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Count, Q, Sum

from apps.portfolio.models import Debtor
from apps.strategy.models import ActionType


def _round_metric(value: Decimal | int | float) -> Decimal:
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _round_money(value: Decimal | int | float) -> Decimal:
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _format_compact_money(value: Decimal | int | float) -> str:
    numeric = float(value or 0)
    absolute = abs(numeric)
    if absolute >= 1_000_000:
        return f"{numeric / 1_000_000:.2f}M"
    if absolute >= 1_000:
        return f"{numeric / 1_000:.1f}K"
    return f"{numeric:.2f}"


def _contact_channel(debtor) -> str:
    if debtor.phone_number:
        return ActionType.CALL
    if debtor.email:
        return ActionType.EMAIL
    return ActionType.SMS


def _payment_total(debtor) -> Decimal:
    return debtor.payments.aggregate(total=Sum('paid_amount'))['total'] or Decimal('0.00')


def _broken_promise_count(debtor) -> int:
    return debtor.promises_to_pay.filter(status='broken').count()


def _recent_ptp_count(debtor) -> int:
    return debtor.promises_to_pay.filter(status='pending').count()


def _contactability_score(debtor) -> Decimal:
    score = Decimal('0.00')
    if debtor.phone_number:
        score += Decimal('0.65')
    if debtor.email:
        score += Decimal('0.35')
    return min(score, Decimal('1.00'))


def _action_decision(debtor, *, contactability_score: Decimal, broken_promises: int, pending_promises: int) -> tuple[str, str, Decimal, str]:
    outstanding_total = Decimal(debtor.outstanding_total)
    status = (debtor.status or '').lower()
    dpd = debtor.days_past_due

    if status in {'closed', 'paying'}:
        return (
            ActionType.MONITOR,
            ActionType.MONITOR,
            Decimal('1.50'),
            'Account is already resolving, so monitoring is better than pushing a new action.',
        )

    if broken_promises >= 1 and outstanding_total >= Decimal('3500'):
        return (
            ActionType.SETTLEMENT,
            _contact_channel(debtor),
            Decimal('8.50'),
            'Broken payment promises and higher balance make a settlement path more attractive than another generic contact attempt.',
        )

    if dpd >= 180 and contactability_score == Decimal('0.00'):
        return (
            ActionType.LEGAL_REVIEW,
            ActionType.LEGAL_REVIEW,
            Decimal('4.50'),
            'Severe aging with no contact channel suggests legal review rather than standard outreach.',
        )

    if status == 'promise_to_pay' or pending_promises >= 1:
        return (
            ActionType.CALL,
            ActionType.CALL if debtor.phone_number else _contact_channel(debtor),
            Decimal('6.00'),
            'An active promise-to-pay needs direct follow-up to convert intent into cash collection.',
        )

    if dpd >= 120 and debtor.phone_number:
        return (
            ActionType.CALL,
            ActionType.CALL,
            Decimal('5.25'),
            'Late-stage delinquency with direct phone reach should move into an immediate call-first action.',
        )

    if dpd >= 90 and debtor.email and not debtor.phone_number:
        return (
            ActionType.EMAIL,
            ActionType.EMAIL,
            Decimal('3.75'),
            'The account is aging and email is the strongest available digital channel.',
        )

    if outstanding_total <= Decimal('900') and contactability_score > Decimal('0.00'):
        return (
            ActionType.SMS,
            ActionType.SMS,
            Decimal('2.80'),
            'Lower-balance debt is better served by low-cost digital outreach first.',
        )

    if outstanding_total >= Decimal('5000') and contactability_score > Decimal('0.00'):
        return (
            ActionType.SETTLEMENT,
            _contact_channel(debtor),
            Decimal('7.20'),
            'Higher exposure suggests testing a structured settlement path to unlock faster recovery.',
        )

    if contactability_score > Decimal('0.00'):
        channel = _contact_channel(debtor)
        uplift = Decimal('4.20') if channel == ActionType.CALL else Decimal('3.20')
        return (
            channel if channel != ActionType.EMAIL else ActionType.EMAIL,
            channel,
            uplift,
            'The debtor is reachable, so the next best step is a standard contact action through the strongest available channel.',
        )

    return (
        ActionType.MONITOR,
        ActionType.MONITOR,
        Decimal('0.90'),
        'No reliable action channel is available, so the case should stay under monitoring until the profile improves.',
    )


def _priority_score(debtor, *, contactability_score: Decimal, broken_promises: int, pending_promises: int, action_uplift_pct: Decimal) -> Decimal:
    outstanding_total = Decimal(debtor.outstanding_total)
    balance_component = min(outstanding_total / Decimal('120'), Decimal('28.00'))
    dpd_component = min(Decimal(debtor.days_past_due) / Decimal('6'), Decimal('20.00'))
    risk_component = {
        'high': Decimal('22.00'),
        'medium': Decimal('14.00'),
        'low': Decimal('8.00'),
    }.get(debtor.risk_band, Decimal('10.00'))
    contact_component = contactability_score * Decimal('18.00')
    promise_component = Decimal(broken_promises) * Decimal('5.50') + Decimal(pending_promises) * Decimal('4.00')
    uplift_component = min(action_uplift_pct * Decimal('1.90'), Decimal('18.00'))

    if debtor.status == 'new':
        status_component = Decimal('8.00')
    elif debtor.status == 'contacted':
        status_component = Decimal('10.00')
    elif debtor.status == 'promise_to_pay':
        status_component = Decimal('14.00')
    elif debtor.status == 'paying':
        status_component = Decimal('-8.00')
    elif debtor.status == 'closed':
        status_component = Decimal('-18.00')
    else:
        status_component = Decimal('4.00')

    score = balance_component + dpd_component + risk_component + contact_component + promise_component + uplift_component + status_component
    return max(Decimal('0.00'), min(_round_metric(score), Decimal('100.00')))


def _recommendation_payload(debtor):
    contactability_score = _contactability_score(debtor)
    broken_promises = _broken_promise_count(debtor)
    pending_promises = _recent_ptp_count(debtor)
    action, channel, uplift_pct, reason = _action_decision(
        debtor,
        contactability_score=contactability_score,
        broken_promises=broken_promises,
        pending_promises=pending_promises,
    )
    priority_score = _priority_score(
        debtor,
        contactability_score=contactability_score,
        broken_promises=broken_promises,
        pending_promises=pending_promises,
        action_uplift_pct=uplift_pct,
    )
    uplift_amount = _round_money(Decimal(debtor.outstanding_total) * (uplift_pct / Decimal('100')))
    payments_total = _payment_total(debtor)

    return {
        'debtor': debtor,
        'portfolio': debtor.portfolio,
        'recommended_action': action,
        'recommended_action_label': ActionType(action).label,
        'recommended_channel': channel,
        'recommended_channel_label': ActionType(channel).label if channel in ActionType.values else channel.replace('_', ' ').title(),
        'priority_score': priority_score,
        'expected_uplift_pct': _round_metric(uplift_pct),
        'expected_uplift_amount': uplift_amount,
        'expected_uplift_amount_display': _format_compact_money(uplift_amount),
        'outstanding_total': _round_money(debtor.outstanding_total),
        'outstanding_total_display': _format_compact_money(debtor.outstanding_total),
        'payments_total': _round_money(payments_total),
        'payments_total_display': _format_compact_money(payments_total),
        'contactability_score': _round_metric(contactability_score * Decimal('100')),
        'contactability_label': 'Reachable' if contactability_score > Decimal('0.00') else 'No live channel',
        'broken_promises': broken_promises,
        'pending_promises': pending_promises,
        'reason_summary': reason,
        'action_reason': reason,
    }


def build_strategy_workspace(*, portfolio=None):
    debtors = Debtor.objects.select_related('portfolio').prefetch_related('payments', 'promises_to_pay').all()
    if portfolio is not None:
        debtors = debtors.filter(portfolio=portfolio)

    recommendations = [_recommendation_payload(debtor) for debtor in debtors]
    recommendations.sort(key=lambda item: (item['priority_score'], item['expected_uplift_amount']), reverse=True)

    total_uplift = sum((item['expected_uplift_amount'] for item in recommendations), Decimal('0.00'))
    avg_priority = _round_metric(sum((item['priority_score'] for item in recommendations), Decimal('0.00')) / len(recommendations)) if recommendations else Decimal('0.00')
    top_priority = recommendations[0]['priority_score'] if recommendations else Decimal('0.00')

    action_mix = []
    action_counts = {}
    for item in recommendations:
        action_counts[item['recommended_action_label']] = action_counts.get(item['recommended_action_label'], 0) + 1
    for label, count in sorted(action_counts.items(), key=lambda pair: pair[1], reverse=True):
        action_mix.append({'label': label, 'count': count})

    summary = {
        'debtor_count': len(recommendations),
        'top_priority_score': top_priority,
        'avg_priority_score': avg_priority,
        'expected_total_uplift': _round_money(total_uplift),
        'expected_total_uplift_display': _format_compact_money(total_uplift),
        'highest_value_action': action_mix[0]['label'] if action_mix else 'No action',
    }

    return {
        'summary': summary,
        'recommendations': recommendations,
        'action_mix': action_mix,
    }
