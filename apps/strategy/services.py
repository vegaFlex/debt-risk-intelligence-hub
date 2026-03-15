from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Sum

from apps.portfolio.models import CallLog, Debtor
from apps.strategy.models import (
    ActionScenario,
    ActionType,
    CollectorQueueAssignment,
    DebtorActionRecommendation,
    QueueStatus,
    StrategyRun,
    StrategyRunResult,
)


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


def format_compact_money(value: Decimal | int | float) -> str:
    return _format_compact_money(value)


def format_roi_multiple(roi_pct: Decimal | int | float) -> str:
    roi_decimal = Decimal(roi_pct or 0)
    multiple = (roi_decimal / Decimal('100')) + Decimal('1.00')
    return f"{_round_metric(multiple):.2f}"


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


def _contact_history_signals(debtor) -> dict:
    calls = list(debtor.call_logs.order_by('-call_datetime'))
    call_attempt_count = len(calls)
    last_call = calls[0] if calls else None
    last_outcome = last_call.outcome if last_call else ''
    last_outcome_label = last_call.get_outcome_display() if last_call else 'No calls yet'
    no_answer_streak = 0
    refusal_count = 0
    notes_count = 0

    for call in calls:
        if call.outcome == CallLog.Outcome.REFUSED:
            refusal_count += 1
        if (call.notes or '').strip():
            notes_count += 1
        if call.outcome == CallLog.Outcome.NO_ANSWER:
            no_answer_streak += 1
        else:
            break

    wrong_contact_count = sum(1 for call in calls if call.outcome == CallLog.Outcome.WRONG_CONTACT)
    paid_call_count = sum(1 for call in calls if call.outcome == CallLog.Outcome.PAID)
    has_recent_notes = notes_count > 0

    return {
        'call_attempt_count': call_attempt_count,
        'last_call_outcome': last_outcome,
        'last_call_outcome_label': last_outcome_label,
        'no_answer_streak': no_answer_streak,
        'refusal_count': refusal_count,
        'wrong_contact_count': wrong_contact_count,
        'paid_call_count': paid_call_count,
        'notes_count': notes_count,
        'has_recent_notes': has_recent_notes,
    }


def _contactability_score(debtor) -> Decimal:
    score = Decimal('0.00')
    if debtor.phone_number:
        score += Decimal('0.65')
    if debtor.email:
        score += Decimal('0.35')
    return min(score, Decimal('1.00'))


def _action_decision(debtor, *, contactability_score: Decimal, broken_promises: int, pending_promises: int, contact_history: dict) -> tuple[str, str, Decimal, str]:
    outstanding_total = Decimal(debtor.outstanding_total)
    status = (debtor.status or '').lower()
    dpd = debtor.days_past_due

    call_attempt_count = contact_history['call_attempt_count']
    no_answer_streak = contact_history['no_answer_streak']
    refusal_count = contact_history['refusal_count']
    wrong_contact_count = contact_history['wrong_contact_count']
    last_outcome = contact_history['last_call_outcome']

    if status in {'closed', 'paying'}:
        return (
            ActionType.MONITOR,
            ActionType.MONITOR,
            Decimal('1.50'),
            'Account is already resolving, so monitoring is better than pushing a new action.',
        )

    if wrong_contact_count >= 2:
        return (
            ActionType.MONITOR,
            ActionType.MONITOR,
            Decimal('0.60'),
            'Repeated wrong-contact outcomes suggest the case should be monitored until better contact data is available.',
        )

    if no_answer_streak >= 3 and debtor.phone_number and debtor.email:
        return (
            ActionType.EMAIL,
            ActionType.EMAIL,
            Decimal('3.10'),
            'Multiple unanswered calls suggest switching channels before spending another phone attempt.',
        )

    if refusal_count >= 2 and outstanding_total >= Decimal('2500'):
        return (
            ActionType.SETTLEMENT,
            _contact_channel(debtor),
            Decimal('6.90'),
            'Repeated refusals indicate standard outreach is stalling, so a settlement-oriented move is more practical.',
        )

    if broken_promises >= 1 and outstanding_total >= Decimal('3500'):
        return (
            ActionType.SETTLEMENT,
            _contact_channel(debtor),
            Decimal('8.50'),
            'Broken payment promises and higher balance make a settlement path more attractive than another generic contact attempt.',
        )

    if last_outcome == CallLog.Outcome.PROMISE_TO_PAY and pending_promises >= 1:
        return (
            ActionType.CALL,
            ActionType.CALL if debtor.phone_number else _contact_channel(debtor),
            Decimal('6.40'),
            'The most recent contact created a payment promise, so the next best step is a focused follow-up call.',
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


def _priority_score(debtor, *, contactability_score: Decimal, broken_promises: int, pending_promises: int, action_uplift_pct: Decimal, contact_history: dict) -> Decimal:
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
    contact_history_component = Decimal(contact_history['call_attempt_count']) * Decimal('1.25')
    contact_history_component += Decimal(contact_history['broken_promises'] if 'broken_promises' in contact_history else 0)
    if contact_history['no_answer_streak'] >= 3:
        contact_history_component -= Decimal('4.00')
    if contact_history['refusal_count'] >= 2:
        contact_history_component += Decimal('3.50')
    if contact_history['wrong_contact_count'] >= 1:
        contact_history_component -= Decimal('5.00')

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

    score = balance_component + dpd_component + risk_component + contact_component + promise_component + uplift_component + status_component + contact_history_component
    return max(Decimal('0.00'), min(_round_metric(score), Decimal('100.00')))


def _recommendation_payload(debtor):
    contactability_score = _contactability_score(debtor)
    broken_promises = _broken_promise_count(debtor)
    pending_promises = _recent_ptp_count(debtor)
    contact_history = _contact_history_signals(debtor)
    contact_history['broken_promises'] = broken_promises
    action, channel, uplift_pct, reason = _action_decision(
        debtor,
        contactability_score=contactability_score,
        broken_promises=broken_promises,
        pending_promises=pending_promises,
        contact_history=contact_history,
    )
    priority_score = _priority_score(
        debtor,
        contactability_score=contactability_score,
        broken_promises=broken_promises,
        pending_promises=pending_promises,
        action_uplift_pct=uplift_pct,
        contact_history=contact_history,
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
        'call_attempt_count': contact_history['call_attempt_count'],
        'last_call_outcome': contact_history['last_call_outcome'],
        'last_call_outcome_label': contact_history['last_call_outcome_label'],
        'no_answer_streak': contact_history['no_answer_streak'],
        'refusal_count': contact_history['refusal_count'],
        'wrong_contact_count': contact_history['wrong_contact_count'],
        'notes_count': contact_history['notes_count'],
        'has_recent_notes': contact_history['has_recent_notes'],
        'reason_summary': reason,
        'action_reason': reason,
    }


def _strategy_profiles():
    return [
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
            'key': 'balanced',
            'label': 'Balanced Mixed Strategy',
            'description': 'Blend direct outreach, digital recovery, and targeted settlement actions across the queue.',
            'target_actions': {'Call', 'SMS', 'Email', 'Settlement Offer'},
            'uplift_multiplier': Decimal('1.08'),
            'cost_per_case': Decimal('3.80'),
        },
    ]


def _scenario_options(recommendation: dict) -> list[dict]:
    outstanding = recommendation['outstanding_total']
    base_uplift_pct = recommendation['expected_uplift_pct']
    contactability_score = recommendation['contactability_score']
    broken_promises = recommendation['broken_promises']
    pending_promises = recommendation['pending_promises']

    scenarios = [
        {
            'action_type': ActionType.CALL,
            'label': ActionType.CALL.label,
            'channel': 'Phone outreach',
            'uplift_multiplier': Decimal('1.00'),
            'cost': Decimal('4.00'),
            'rationale': 'Best when direct phone reach is available and a fast human follow-up is needed.',
        },
        {
            'action_type': ActionType.SMS,
            'label': ActionType.SMS.label,
            'channel': 'Digital outreach',
            'uplift_multiplier': Decimal('0.62'),
            'cost': Decimal('1.20'),
            'rationale': 'Lower-cost option for lighter-touch nudges or lower-balance accounts.',
        },
        {
            'action_type': ActionType.EMAIL,
            'label': ActionType.EMAIL.label,
            'channel': 'Email outreach',
            'uplift_multiplier': Decimal('0.74'),
            'cost': Decimal('1.60'),
            'rationale': 'Useful when phone attempts are saturated or email is the strongest live channel.',
        },
        {
            'action_type': ActionType.SETTLEMENT,
            'label': ActionType.SETTLEMENT.label,
            'channel': 'Negotiated recovery',
            'uplift_multiplier': Decimal('1.28'),
            'cost': Decimal('7.50'),
            'rationale': 'Higher-touch option for larger balances, repeated refusals, or broken promises.',
        },
        {
            'action_type': ActionType.LEGAL_REVIEW,
            'label': ActionType.LEGAL_REVIEW.label,
            'channel': 'Escalation review',
            'uplift_multiplier': Decimal('0.88'),
            'cost': Decimal('12.00'),
            'rationale': 'Escalation path for aged cases with weak contactability or exhausted outreach.',
        },
        {
            'action_type': ActionType.MONITOR,
            'label': ActionType.MONITOR.label,
            'channel': 'No active outreach',
            'uplift_multiplier': Decimal('0.20'),
            'cost': Decimal('0.50'),
            'rationale': 'Hold position when the account is already resolving or contact data is unreliable.',
        },
    ]

    rows = []
    for scenario in scenarios:
        adjusted_uplift_pct = _round_metric(base_uplift_pct * scenario['uplift_multiplier'])
        if scenario['action_type'] == ActionType.SETTLEMENT and broken_promises >= 1:
            adjusted_uplift_pct = _round_metric(adjusted_uplift_pct + Decimal('1.40'))
        if scenario['action_type'] == ActionType.CALL and pending_promises >= 1:
            adjusted_uplift_pct = _round_metric(adjusted_uplift_pct + Decimal('0.90'))
        if scenario['action_type'] in {ActionType.SMS, ActionType.EMAIL} and contactability_score < Decimal('40.00'):
            adjusted_uplift_pct = _round_metric(max(Decimal('0.40'), adjusted_uplift_pct - Decimal('0.80')))
        if scenario['action_type'] == ActionType.LEGAL_REVIEW and recommendation['wrong_contact_count'] >= 2:
            adjusted_uplift_pct = _round_metric(adjusted_uplift_pct + Decimal('0.60'))

        expected_uplift_amount = _round_money(outstanding * (adjusted_uplift_pct / Decimal('100')))
        projected_recovery = _round_money(recommendation['payments_total'] + expected_uplift_amount)
        cost = scenario['cost']
        projected_roi = Decimal('0.00')
        if cost > 0:
            projected_roi = _round_metric(((expected_uplift_amount - cost) / cost) * Decimal('100'))

        rows.append({
            'action_type': scenario['action_type'],
            'label': scenario['label'],
            'channel': scenario['channel'],
            'expected_uplift_pct': adjusted_uplift_pct,
            'expected_uplift_amount': expected_uplift_amount,
            'expected_uplift_amount_display': _format_compact_money(expected_uplift_amount),
            'projected_recovery': projected_recovery,
            'projected_recovery_display': _format_compact_money(projected_recovery),
            'estimated_cost': cost,
            'estimated_cost_display': _format_compact_money(cost),
            'projected_roi': projected_roi,
            'rationale': scenario['rationale'],
            'is_recommended': scenario['action_type'] == recommendation['recommended_action'],
        })

    rows.sort(key=lambda item: (item['is_recommended'], item['projected_roi'], item['expected_uplift_amount']), reverse=True)
    return rows


def build_debtor_strategy_detail(debtor: Debtor) -> dict:
    debtor = Debtor.objects.select_related('portfolio').prefetch_related('payments', 'promises_to_pay', 'call_logs').get(id=debtor.id)
    recommendation = _recommendation_payload(debtor)
    call_logs = list(debtor.call_logs.select_related('agent')[:8])
    promises = list(debtor.promises_to_pay.select_related('fulfilled_payment', 'call_log')[:6])
    scenarios = _scenario_options(recommendation)

    overview = {
        'status': debtor.status.replace('_', ' ').title(),
        'risk_band': debtor.get_risk_band_display(),
        'days_past_due': debtor.days_past_due,
        'outstanding_total_display': recommendation['outstanding_total_display'],
        'payments_total_display': recommendation['payments_total_display'],
        'contactability_label': recommendation['contactability_label'],
        'contactability_score': recommendation['contactability_score'],
    }

    signals = [
        {'label': 'Call Attempts', 'value': recommendation['call_attempt_count'], 'meta': 'Recent contact volume'},
        {'label': 'Last Outcome', 'value': recommendation['last_call_outcome_label'], 'meta': 'Most recent call result'},
        {'label': 'No-Answer Streak', 'value': recommendation['no_answer_streak'], 'meta': 'Consecutive unanswered calls'},
        {'label': 'Refusals', 'value': recommendation['refusal_count'], 'meta': 'Refusal outcomes logged'},
        {'label': 'Broken Promises', 'value': recommendation['broken_promises'], 'meta': 'Promises not kept'},
        {'label': 'Pending Promises', 'value': recommendation['pending_promises'], 'meta': 'Open promise-to-pay items'},
    ]

    return {
        'debtor': debtor,
        'portfolio': debtor.portfolio,
        'recommendation': recommendation,
        'overview': overview,
        'signals': signals,
        'call_logs': call_logs,
        'promises': promises,
        'scenarios': scenarios,
    }


def _scope_strategy_debtors(debtors, *, max_debtors=None):
    if hasattr(debtors, 'select_related'):
        scoped = debtors.select_related('portfolio')
        if max_debtors:
            scoped = scoped.order_by('-risk_score', '-outstanding_total', 'id')[:max_debtors]
        return scoped.prefetch_related('payments', 'promises_to_pay', 'call_logs')
    return debtors


def build_strategy_workspace(*, portfolio=None, debtors=None, max_debtors=None):
    if debtors is None:
        debtors = Debtor.objects.all()
        if portfolio is not None:
            debtors = debtors.filter(portfolio=portfolio)
    debtors = _scope_strategy_debtors(debtors, max_debtors=max_debtors)

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



def build_collector_queue(*, portfolio=None, debtors=None, queue_limit: int = 30, max_debtors=None):
    workspace = build_strategy_workspace(portfolio=portfolio, debtors=debtors, max_debtors=max_debtors)
    recommendations = workspace['recommendations']

    collectors = ('Lane Alpha', 'Lane Bravo', 'Lane Charlie')
    queue_rows = []
    collector_load = {name: [] for name in collectors}

    lane_preview_limit = 5
    snapshot_items = recommendations[:queue_limit]

    for index, item in enumerate(snapshot_items, start=1):
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
        'expected_total_uplift': workspace['summary']['expected_total_uplift'],
        'expected_uplift_display': workspace['summary']['expected_total_uplift_display'],
        'top_action': workspace['summary']['highest_value_action'],
        'queue_limit': queue_limit,
        'lane_count': len(collectors),
    }

    collector_cards = []
    for collector_name, items in collector_load.items():
        if not items:
            continue
        total_uplift = sum((entry['expected_uplift_amount'] for entry in items), Decimal('0.00'))
        action_mix = {}
        for entry in items:
            action_mix[entry['recommended_action_label']] = action_mix.get(entry['recommended_action_label'], 0) + 1
        top_action_label, top_action_count = sorted(action_mix.items(), key=lambda pair: pair[1], reverse=True)[0]
        collector_cards.append({
            'collector_name': collector_name,
            'case_count': len(items),
            'top_priority': items[0]['priority_score'],
            'expected_uplift_display': _format_compact_money(total_uplift),
            'top_action_label': top_action_label,
            'top_action_count': top_action_count,
            'actions': items[:lane_preview_limit],
            'preview_count': min(len(items), lane_preview_limit),
        })

    return {
        'queue_summary': queue_summary,
        'queue_rows': queue_rows,
        'collector_cards': collector_cards,
    }



def build_strategy_simulator(*, portfolio=None, debtors=None, max_debtors=None):
    workspace = build_strategy_workspace(portfolio=portfolio, debtors=debtors, max_debtors=max_debtors)
    recommendations = workspace['recommendations']

    strategy_rows = []
    for profile in _strategy_profiles():
        targeted = [
            item for item in recommendations
            if item['recommended_action_label'] in profile['target_actions']
        ]
        if not targeted and profile['key'] == 'balanced':
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
            'expected_roi_multiple': format_roi_multiple(expected_roi),
            'avg_priority_score': avg_priority,
            'best_fit_segments': best_fit or ['General queue'],
            'top_cases': targeted[:5],
            'targeted_cases': targeted,
        })

    strategy_rows.sort(key=lambda item: (item['expected_roi'], item['expected_total_uplift']), reverse=True)

    winner = strategy_rows[0] if strategy_rows else None
    simulator_summary = {
        'strategy_count': len(strategy_rows),
        'best_strategy': winner['label'] if winner else 'No strategy',
        'best_roi': winner['expected_roi'] if winner else Decimal('0.00'),
        'best_roi_multiple': winner['expected_roi_multiple'] if winner else '1.00',
        'best_uplift_display': winner['expected_total_uplift_display'] if winner else '0.00',
        'targeted_cases': winner['debtor_count'] if winner else 0,
    }

    return {
        'simulator_summary': simulator_summary,
        'strategy_rows': strategy_rows,
        'winner': winner,
    }


def save_strategy_run(*, portfolio, created_by, strategy_key: str | None = None, notes: str = ''):
    workspace = build_strategy_workspace(portfolio=portfolio)
    simulator = build_strategy_simulator(portfolio=portfolio)
    queue = build_collector_queue(portfolio=portfolio)

    selected = None
    if strategy_key:
        selected = next((row for row in simulator['strategy_rows'] if row['key'] == strategy_key), None)
    if selected is None:
        selected = simulator['winner']
    if selected is None:
        return None

    run_name = f"{selected['label']} - {portfolio.name}"
    run_notes = notes.strip() or f"Saved from strategy simulator for {portfolio.name}."

    with transaction.atomic():
        strategy_run = StrategyRun.objects.create(
            name=run_name,
            portfolio=portfolio,
            strategy_type=selected['key'],
            created_by=created_by,
            notes=run_notes,
        )
        StrategyRunResult.objects.create(
            strategy_run=strategy_run,
            debtor_count=selected['debtor_count'],
            expected_total_recovery=selected['expected_total_recovery'],
            expected_total_uplift=selected['expected_total_uplift'],
            expected_cost=selected['expected_cost'],
            expected_roi=selected['expected_roi'],
            notes=selected['description'],
        )

        DebtorActionRecommendation.objects.bulk_create([
            DebtorActionRecommendation(
                debtor=item['debtor'],
                recommended_action=item['recommended_action'],
                recommended_channel=item['recommended_channel'],
                priority_score=item['priority_score'],
                expected_uplift_pct=item['expected_uplift_pct'],
                expected_uplift_amount=item['expected_uplift_amount'],
                reason_summary=item['reason_summary'],
                model_version='strategy-rules-v2',
            )
            for item in workspace['recommendations']
        ])

        ActionScenario.objects.bulk_create([
            ActionScenario(
                debtor=item['debtor'],
                action_type=item['recommended_action'],
                expected_recovery_pct=item['expected_uplift_pct'],
                expected_recovery_amount=item['payments_total'] + item['expected_uplift_amount'],
                expected_uplift_pct=item['expected_uplift_pct'],
                estimated_cost=selected['expected_cost'] / max(selected['debtor_count'], 1),
                estimated_roi=selected['expected_roi'],
            )
            for item in selected['targeted_cases']
        ])

        for item in queue['queue_rows']:
            CollectorQueueAssignment.objects.update_or_create(
                collector_name=item['collector_name'],
                priority_rank=item['queue_rank'],
                defaults={
                    'debtor': item['debtor'],
                    'action_type': item['recommended_action'],
                    'status': QueueStatus.QUEUED,
                },
            )

    return strategy_run
