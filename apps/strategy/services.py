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



def build_collector_queue(*, portfolio=None):
    workspace = build_strategy_workspace(portfolio=portfolio)
    recommendations = workspace['recommendations']

    collectors = ('Team Alpha', 'Team Bravo', 'Team Charlie')
    queue_rows = []
    collector_load = {name: [] for name in collectors}

    for index, item in enumerate(recommendations[:30], start=1):
        collector_name = collectors[(index - 1) % len(collectors)]
        lane_position = len(collector_load[collector_name]) + 1
        queue_item = {
            **item,
            'queue_rank': index,
            'collector_name': collector_name,
            'lane_position': lane_position,
            'priority_bucket': (
                'Act Now' if item['priority_score'] >= Decimal('75.00')
                else 'Review Today' if item['priority_score'] >= Decimal('55.00')
                else 'Monitor Queue'
            ),
        }
        collector_load[collector_name].append(queue_item)
        queue_rows.append(queue_item)

    queue_summary = {
        'queued_cases': len(queue_rows),
        'act_now_cases': sum(1 for item in queue_rows if item['priority_bucket'] == 'Act Now'),
        'avg_priority_score': workspace['summary']['avg_priority_score'],
        'expected_uplift_display': workspace['summary']['expected_total_uplift_display'],
        'top_action': workspace['summary']['highest_value_action'],
    }

    collector_cards = []
    for collector_name, items in collector_load.items():
        if not items:
            continue
        total_uplift = sum((entry['expected_uplift_amount'] for entry in items), Decimal('0.00'))
        collector_cards.append({
            'collector_name': collector_name,
            'case_count': len(items),
            'top_priority': items[0]['priority_score'],
            'expected_uplift_display': _format_compact_money(total_uplift),
            'actions': items[:5],
        })

    return {
        'queue_summary': queue_summary,
        'queue_rows': queue_rows,
        'collector_cards': collector_cards,
    }



def build_strategy_simulator(*, portfolio=None):
    workspace = build_strategy_workspace(portfolio=portfolio)
    recommendations = workspace['recommendations']

    strategy_profiles = [
        {
            'key': 'call_first',
            'label': 'Call-First Strategy',
            'description': 'Push high-touch phone outreach on the most recoverable and urgent cases first.',
            'target_actions': {'Call'},
            'uplift_multiplier': Decimal('1.12'),
            'cost_per_case': Decimal('4.00'),
        },
        {
            'key': 'digital_first',
            'label': 'Digital-First Strategy',
            'description': 'Lean on lower-cost SMS and email actions before escalating to higher-touch channels.',
            'target_actions': {'SMS', 'Email'},
            'uplift_multiplier': Decimal('0.95'),
            'cost_per_case': Decimal('1.50'),
        },
        {
            'key': 'settlement_first',
            'label': 'Settlement Strategy',
            'description': 'Focus on higher-balance and broken-promise cases with settlement-led recovery moves.',
            'target_actions': {'Settlement Offer'},
            'uplift_multiplier': Decimal('1.28'),
            'cost_per_case': Decimal('7.50'),
        },
        {
            'key': 'legal_escalation',
            'label': 'Legal Escalation Strategy',
            'description': 'Escalate the hardest late-stage cases where standard contact channels have little traction.',
            'target_actions': {'Legal Review'},
            'uplift_multiplier': Decimal('1.20'),
            'cost_per_case': Decimal('12.00'),
        },
        {
            'key': 'balanced_mix',
            'label': 'Balanced Mixed Strategy',
            'description': 'Blend direct outreach, digital recovery, and targeted settlement actions across the queue.',
            'target_actions': {'Call', 'SMS', 'Email', 'Settlement Offer'},
            'uplift_multiplier': Decimal('1.08'),
            'cost_per_case': Decimal('3.80'),
        },
    ]

    strategy_rows = []
    for profile in strategy_profiles:
        targeted = [
            item for item in recommendations
            if item['recommended_action_label'] in profile['target_actions']
        ]
        if not targeted and profile['key'] == 'balanced_mix':
            targeted = recommendations[: min(20, len(recommendations))]

        debtor_count = len(targeted)
        base_uplift = sum((item['expected_uplift_amount'] for item in targeted), Decimal('0.00'))
        expected_total_uplift = _round_money(base_uplift * profile['uplift_multiplier'])
        expected_cost = _round_money(Decimal(debtor_count) * profile['cost_per_case'])
        expected_total_recovery = _round_money(sum((item['payments_total'] + item['expected_uplift_amount'] for item in targeted), Decimal('0.00')) + expected_total_uplift)

        expected_roi = Decimal('0.00')
        if expected_cost > 0:
            expected_roi = _round_metric(((expected_total_uplift - expected_cost) / expected_cost) * Decimal('100'))

        avg_priority = _round_metric(sum((item['priority_score'] for item in targeted), Decimal('0.00')) / debtor_count) if debtor_count else Decimal('0.00')

        best_fit = []
        for action_label in profile['target_actions']:
            action_count = sum(1 for item in targeted if item['recommended_action_label'] == action_label)
            if action_count:
                best_fit.append(f'{action_label} ({action_count})')

        strategy_rows.append({
            'key': profile['key'],
            'label': profile['label'],
            'description': profile['description'],
            'debtor_count': debtor_count,
            'expected_total_recovery': expected_total_recovery,
            'expected_total_recovery_display': _format_compact_money(expected_total_recovery),
            'expected_total_uplift': expected_total_uplift,
            'expected_total_uplift_display': _format_compact_money(expected_total_uplift),
            'expected_cost': expected_cost,
            'expected_cost_display': _format_compact_money(expected_cost),
            'expected_roi': expected_roi,
            'avg_priority_score': avg_priority,
            'best_fit_segments': best_fit or ['General queue'],
            'top_cases': targeted[:5],
        })

    strategy_rows.sort(key=lambda item: (item['expected_roi'], item['expected_total_uplift']), reverse=True)

    winner = strategy_rows[0] if strategy_rows else None
    simulator_summary = {
        'strategy_count': len(strategy_rows),
        'best_strategy': winner['label'] if winner else 'No strategy',
        'best_roi': winner['expected_roi'] if winner else Decimal('0.00'),
        'best_uplift_display': winner['expected_total_uplift_display'] if winner else '0.00',
        'targeted_cases': winner['debtor_count'] if winner else 0,
    }

    return {
        'simulator_summary': simulator_summary,
        'strategy_rows': strategy_rows,
        'winner': winner,
    }
