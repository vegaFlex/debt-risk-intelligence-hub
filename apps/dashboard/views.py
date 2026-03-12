from decimal import Decimal
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import render

from apps.portfolio.models import Debtor, Payment, Portfolio
from apps.users.decorators import viewer_or_manager_or_admin_required


DEFAULT_STATUS_OPTIONS = [
    ('new', 'New'),
    ('contacted', 'Contacted'),
    ('promise_to_pay', 'Promise To Pay'),
    ('paying', 'Paying'),
    ('closed', 'Closed'),
]

ORDERABLE_COLUMNS = {
    'full_name': 'full_name',
    'portfolio': 'portfolio__name',
    'status': 'status',
    'days_past_due': 'days_past_due',
    'outstanding_total': 'outstanding_total',
    'risk_score': 'risk_score',
    'risk_band': 'risk_band',
}

SORT_LABELS = {
    'full_name': 'debtor',
    'portfolio': 'portfolio',
    'status': 'status',
    'days_past_due': 'days past due',
    'outstanding_total': 'outstanding total',
    'risk_score': 'risk score',
    'risk_band': 'risk band',
}

DEFAULT_SORT = 'risk_score'
DEFAULT_DIRECTION = 'desc'
PAGE_SIZE = 15


def _format_compact_number(value):
    number = float(value)
    abs_number = abs(number)
    if abs_number >= 1_000_000:
        return f"{number / 1_000_000:.2f}M"
    if abs_number >= 1_000:
        return f"{number / 1_000:.1f}K"
    return f"{number:,.2f}"


def _build_status_options():
    known_values = {value for value, _ in DEFAULT_STATUS_OPTIONS}
    options = list(DEFAULT_STATUS_OPTIONS)

    dynamic_values = (
        Debtor.objects.exclude(status='')
        .values_list('status', flat=True)
        .distinct()
    )
    for value in dynamic_values:
        if value not in known_values:
            options.append((value, value.replace('_', ' ').title()))
            known_values.add(value)

    return options


def _build_ordering(sort_key, direction):
    sort_field = ORDERABLE_COLUMNS.get(sort_key, ORDERABLE_COLUMNS[DEFAULT_SORT])
    prefix = '-' if direction == 'desc' else ''
    ordering = [f'{prefix}{sort_field}']

    if sort_field != 'risk_score':
        ordering.append('-risk_score')
    if sort_field != 'outstanding_total':
        ordering.append('-outstanding_total')
    ordering.append('id')
    return ordering


def _build_query_string(params, **updates):
    query = {k: v for k, v in params.items() if v not in ('', None)}
    for key, value in updates.items():
        if value in ('', None):
            query.pop(key, None)
        else:
            query[key] = value
    return urlencode(query)


def _current_filters(request, status_options):
    sort = request.GET.get('sort', DEFAULT_SORT)
    direction = request.GET.get('direction', DEFAULT_DIRECTION)
    status = request.GET.get('status', '')

    if sort not in ORDERABLE_COLUMNS:
        sort = DEFAULT_SORT
    if direction not in {'asc', 'desc'}:
        direction = DEFAULT_DIRECTION

    allowed_statuses = {value for value, _ in status_options}
    status = status if status in allowed_statuses else ''

    return {
        'portfolio': request.GET.get('portfolio', ''),
        'risk_band': request.GET.get('risk_band', ''),
        'status': status,
        'date_from': request.GET.get('date_from', ''),
        'date_to': request.GET.get('date_to', ''),
        'sort': sort,
        'direction': direction,
        'page': request.GET.get('page', '1'),
    }


def _filtered_debtors(filters):
    debtors = Debtor.objects.select_related('portfolio').all()

    if filters['portfolio']:
        debtors = debtors.filter(portfolio_id=filters['portfolio'])
    if filters['risk_band']:
        debtors = debtors.filter(risk_band=filters['risk_band'])
    if filters['status']:
        debtors = debtors.filter(status=filters['status'])
    if filters['date_from']:
        debtors = debtors.filter(created_at__date__gte=filters['date_from'])
    if filters['date_to']:
        debtors = debtors.filter(created_at__date__lte=filters['date_to'])

    return debtors


def _chart_context(filtered_debtors, status_options, filters):
    zero_decimal = Value(Decimal('0.00'), output_field=DecimalField(max_digits=14, decimal_places=2))
    risk_order = [('high', 'High'), ('medium', 'Medium'), ('low', 'Low')]

    risk_counts = {
        row['risk_band']: row['count']
        for row in filtered_debtors.values('risk_band').annotate(count=Count('id'))
    }
    risk_chart = {
        'labels': [label for key, label in risk_order if risk_counts.get(key)],
        'values': [risk_counts.get(key, 0) for key, _label in risk_order if risk_counts.get(key)],
        'colors': ['#b42318', '#b45309', '#067647'][: len([key for key, _label in risk_order if risk_counts.get(key)])],
    }

    status_counts = {
        row['status']: row['count']
        for row in filtered_debtors.values('status').annotate(count=Count('id'))
    }
    status_chart = {
        'labels': [],
        'values': [],
        'colors': [],
    }
    status_palette = ['#0f766e', '#0b4d47', '#7c3aed', '#b45309', '#64748b', '#b42318']
    for index, (value, label) in enumerate(status_options):
        count = status_counts.get(value, 0)
        if count:
            status_chart['labels'].append(label)
            status_chart['values'].append(count)
            status_chart['colors'].append(status_palette[index % len(status_palette)])

    segment_rows = list(
        filtered_debtors.values('portfolio__name', 'risk_band')
        .annotate(total_outstanding=Coalesce(Sum('outstanding_total'), zero_decimal))
        .order_by('-total_outstanding', 'portfolio__name')
    )

    if filters['portfolio']:
        visible_segments = segment_rows
    else:
        visible_segments = segment_rows[:5]
        if len(segment_rows) > 5:
            others_total = round(sum(float(row['total_outstanding']) for row in segment_rows[5:]), 2)
            if others_total:
                visible_segments.append({
                    'portfolio__name': 'Others',
                    'risk_band': 'mixed',
                    'total_outstanding': others_total,
                })

    exposure_labels = []
    exposure_values = []
    for row in visible_segments:
        if row['portfolio__name'] == 'Others':
            exposure_labels.append('Others')
            exposure_values.append(float(row['total_outstanding']))
        else:
            exposure_labels.append(f"{row['portfolio__name']} - {row['risk_band'].title()}")
            exposure_values.append(float(row['total_outstanding']))

    exposure_chart = {
        'labels': exposure_labels,
        'values': [round(value, 2) for value in exposure_values],
        'colors': ['#0f766e', '#0b4d47', '#2f855a', '#b45309', '#b42318', '#64748b'][: len(exposure_labels)],
    }

    return {
        'risk_band_distribution': risk_chart,
        'status_distribution': status_chart,
        'outstanding_exposure': exposure_chart,
    }


def _kpis_and_segments(filtered_debtors):
    zero_decimal = Value(Decimal('0.00'), output_field=DecimalField(max_digits=14, decimal_places=2))

    total_debtors = filtered_debtors.count()
    outstanding_total = filtered_debtors.aggregate(value=Coalesce(Sum('outstanding_total'), zero_decimal))['value']
    collected_total = Payment.objects.filter(debtor__in=filtered_debtors).aggregate(
        value=Coalesce(Sum('paid_amount'), zero_decimal)
    )['value']

    contacted_statuses = ['contacted', 'promise_to_pay', 'paying', 'closed']
    contacted_count = filtered_debtors.filter(status__in=contacted_statuses).count()
    ptp_count = filtered_debtors.filter(status='promise_to_pay').count()
    paying_count = filtered_debtors.filter(status='paying').count()

    low_total = filtered_debtors.filter(risk_band='low').aggregate(value=Coalesce(Sum('outstanding_total'), zero_decimal))['value']
    medium_total = filtered_debtors.filter(risk_band='medium').aggregate(value=Coalesce(Sum('outstanding_total'), zero_decimal))['value']
    high_total = filtered_debtors.filter(risk_band='high').aggregate(value=Coalesce(Sum('outstanding_total'), zero_decimal))['value']

    expected_collections = (
        (low_total * Decimal('0.65'))
        + (medium_total * Decimal('0.40'))
        + (high_total * Decimal('0.20'))
    )

    contact_rate = (contacted_count / total_debtors * 100) if total_debtors else 0
    ptp_rate = (ptp_count / contacted_count * 100) if contacted_count else 0
    conversion_rate = (paying_count / contacted_count * 100) if contacted_count else 0
    recovery_rate = (collected_total / outstanding_total * 100) if outstanding_total else 0

    top_risk_segments = (
        filtered_debtors.values('portfolio__name', 'risk_band', 'status')
        .annotate(
            debtor_count=Count('id'),
            total_outstanding=Coalesce(Sum('outstanding_total'), zero_decimal),
        )
        .order_by('-debtor_count', '-total_outstanding')[:8]
    )

    return {
        'kpis': {
            'total_debtors': total_debtors,
            'contact_rate': round(contact_rate, 2),
            'ptp_rate': round(ptp_rate, 2),
            'conversion_rate': round(conversion_rate, 2),
            'recovery_rate': round(float(recovery_rate), 2),
            'expected_collections': round(float(expected_collections), 2),
            'expected_collections_display': _format_compact_number(expected_collections),
        },
        'performance': {
            'contacted_count': contacted_count,
            'ptp_count': ptp_count,
            'paying_count': paying_count,
            'open_cases': filtered_debtors.exclude(status='closed').count(),
        },
        'top_risk_segments': top_risk_segments,
    }


def _list_context(filters, filtered_debtors, *, anchor):
    ordered_debtors = filtered_debtors.order_by(*_build_ordering(filters['sort'], filters['direction']))
    paginator = Paginator(ordered_debtors, PAGE_SIZE)
    results_page = paginator.get_page(filters['page'])
    page_range = paginator.get_elided_page_range(number=results_page.number, on_each_side=1, on_ends=1)

    active_params = {
        'portfolio': filters['portfolio'],
        'risk_band': filters['risk_band'],
        'status': filters['status'],
        'date_from': filters['date_from'],
        'date_to': filters['date_to'],
        'sort': filters['sort'],
        'direction': filters['direction'],
    }

    sort_links = {}
    sort_state = {}
    for key in ORDERABLE_COLUMNS:
        next_direction = 'desc' if filters['sort'] == key and filters['direction'] == 'asc' else 'asc'
        sort_links[key] = f"{_build_query_string(active_params, sort=key, direction=next_direction, page='1')}#{anchor}"
        sort_state[key] = {
            'is_active': filters['sort'] == key,
            'direction': filters['direction'] if filters['sort'] == key else '',
        }

    page_links = {
        'prev': f"{_build_query_string(active_params, page=results_page.previous_page_number())}#{anchor}" if results_page.has_previous() else '',
        'next': f"{_build_query_string(active_params, page=results_page.next_page_number())}#{anchor}" if results_page.has_next() else '',
        'numbers': [
            {
                'label': str(page_value),
                'query': f"{_build_query_string(active_params, page=page_value)}#{anchor}" if str(page_value) != '…' else '',
                'is_current': str(page_value) == str(results_page.number),
                'is_ellipsis': str(page_value) == '…',
            }
            for page_value in page_range
        ],
    }

    return {
        'results_page': results_page,
        'sort_links': sort_links,
        'sort_state': sort_state,
        'page_links': page_links,
        'ordering': {
            'sort': filters['sort'],
            'direction': filters['direction'],
            'label': SORT_LABELS.get(filters['sort'], SORT_LABELS[DEFAULT_SORT]),
        },
    }


def _base_context(filters, status_options):
    return {
        'filters': {
            'portfolio': filters['portfolio'],
            'risk_band': filters['risk_band'],
            'status': filters['status'],
            'date_from': filters['date_from'],
            'date_to': filters['date_to'],
        },
        'portfolios': Portfolio.objects.order_by('name'),
        'status_options': status_options,
    }


def _navigation_actions(filters, user):
    base = {
        'portfolio': filters['portfolio'],
        'risk_band': filters['risk_band'],
        'status': filters['status'],
        'date_from': filters['date_from'],
        'date_to': filters['date_to'],
        'sort': filters['sort'],
        'direction': filters['direction'],
    }

    def debtors_link(label, **updates):
        query = _build_query_string(base, **updates)
        return {'label': label, 'href': f'/dashboard/debtors/?{query}#debtor-results'}

    primary = [
        debtors_link('Full Debtor List'),
        {'label': 'Report Preview', 'href': f"/reports/management/?{_build_query_string({'date_from': filters['date_from'], 'date_to': filters['date_to']})}"},
    ]

    secondary = [
        debtors_link('High Risk Cases', risk_band='high'),
        debtors_link('PTP Cases', status='promise_to_pay'),
        debtors_link('Paying Cases', status='paying'),
        debtors_link('Open Cases', status='new'),
        {'label': 'API Portfolios', 'href': '/api/portfolios/'},
        {'label': 'API Debtors', 'href': '/api/debtors/'},
        {'label': 'API KPIs', 'href': '/api/kpis/overview/'},
    ]

    if getattr(user, 'role', '') in {'manager', 'admin'}:
        secondary[4:4] = [
            {'label': 'Excel Report', 'href': f"/reports/management/excel/?{_build_query_string({'date_from': filters['date_from'], 'date_to': filters['date_to']})}"},
            {'label': 'PDF Report', 'href': f"/reports/management/pdf/?{_build_query_string({'date_from': filters['date_from'], 'date_to': filters['date_to']})}"},
        ]

    admin_href = ''
    if user.is_superuser or getattr(user, 'role', '') == 'admin':
        admin_href = '/admin/'

    return {'primary': primary, 'secondary': secondary, 'admin_href': admin_href}


@login_required
@viewer_or_manager_or_admin_required
def management_dashboard_view(request):
    status_options = _build_status_options()
    filters = _current_filters(request, status_options)
    filtered_debtors = _filtered_debtors(filters)

    context = _base_context(filters, status_options)
    context.update(_kpis_and_segments(filtered_debtors))
    context['chart_data'] = _chart_context(filtered_debtors, status_options, filters)
    context.update({
        'top_risk_debtors': filtered_debtors.order_by('-risk_score', '-outstanding_total', 'id')[:15],
        'full_list_query': _build_query_string({
            'portfolio': filters['portfolio'],
            'risk_band': filters['risk_band'],
            'status': filters['status'],
            'date_from': filters['date_from'],
            'date_to': filters['date_to'],
            'sort': filters['sort'],
            'direction': filters['direction'],
        }),
        'nav_actions': _navigation_actions(filters, request.user),
    })
    return render(request, 'dashboard/management_dashboard.html', context)


@login_required
@viewer_or_manager_or_admin_required
def debtor_results_view(request):
    status_options = _build_status_options()
    filters = _current_filters(request, status_options)
    filtered_debtors = _filtered_debtors(filters)

    context = _base_context(filters, status_options)
    context.update(_kpis_and_segments(filtered_debtors))
    context.update(_list_context(filters, filtered_debtors, anchor='debtor-results'))
    context.update({'nav_actions': _navigation_actions(filters, request.user)})
    return render(request, 'dashboard/debtor_results.html', context)
