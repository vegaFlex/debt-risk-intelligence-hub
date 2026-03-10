from decimal import Decimal
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from apps.users.decorators import manager_or_admin_required

from apps.portfolio.models import Debtor, Payment, Portfolio


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

DEFAULT_SORT = 'risk_score'
DEFAULT_DIRECTION = 'desc'
PAGE_SIZE = 25


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


@login_required
@manager_or_admin_required
def management_dashboard_view(request):
    portfolio_id = request.GET.get('portfolio')
    risk_band = request.GET.get('risk_band')
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    sort = request.GET.get('sort', DEFAULT_SORT)
    direction = request.GET.get('direction', DEFAULT_DIRECTION)
    page_number = request.GET.get('page', '1')

    if sort not in ORDERABLE_COLUMNS:
        sort = DEFAULT_SORT
    if direction not in {'asc', 'desc'}:
        direction = DEFAULT_DIRECTION

    status_options = _build_status_options()
    allowed_statuses = {value for value, _ in status_options}
    status = status if status in allowed_statuses else ''

    debtors = Debtor.objects.select_related('portfolio').all()

    if portfolio_id:
        debtors = debtors.filter(portfolio_id=portfolio_id)
    if risk_band:
        debtors = debtors.filter(risk_band=risk_band)
    if status:
        debtors = debtors.filter(status=status)
    if date_from:
        debtors = debtors.filter(created_at__date__gte=date_from)
    if date_to:
        debtors = debtors.filter(created_at__date__lte=date_to)

    filtered_debtors = debtors.order_by(*_build_ordering(sort, direction))

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
    medium_total = filtered_debtors.filter(risk_band='medium').aggregate(
        value=Coalesce(Sum('outstanding_total'), zero_decimal)
    )['value']
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

    paginator = Paginator(filtered_debtors, PAGE_SIZE)
    results_page = paginator.get_page(page_number)
    page_range = paginator.get_elided_page_range(number=results_page.number, on_each_side=1, on_ends=1)

    current_filters = {
        'portfolio': portfolio_id or '',
        'risk_band': risk_band or '',
        'status': status or '',
        'date_from': date_from or '',
        'date_to': date_to or '',
        'sort': sort,
        'direction': direction,
    }

    sort_links = {}
    for key in ORDERABLE_COLUMNS:
        next_direction = 'asc'
        if sort == key and direction == 'asc':
            next_direction = 'desc'
        sort_links[key] = _build_query_string(current_filters, sort=key, direction=next_direction, page='1')

    page_links = {
        'prev': _build_query_string(current_filters, page=results_page.previous_page_number()) if results_page.has_previous() else '',
        'next': _build_query_string(current_filters, page=results_page.next_page_number()) if results_page.has_next() else '',
        'numbers': [
            {
                'label': str(page_value),
                'query': _build_query_string(current_filters, page=page_value),
                'is_current': str(page_value) == str(results_page.number),
                'is_ellipsis': str(page_value) == '…',
            }
            for page_value in page_range
        ],
    }

    context = {
        'kpis': {
            'total_debtors': total_debtors,
            'contact_rate': round(contact_rate, 2),
            'ptp_rate': round(ptp_rate, 2),
            'conversion_rate': round(conversion_rate, 2),
            'recovery_rate': round(float(recovery_rate), 2),
            'expected_collections': round(float(expected_collections), 2),
        },
        'performance': {
            'contacted_count': contacted_count,
            'ptp_count': ptp_count,
            'paying_count': paying_count,
            'open_cases': filtered_debtors.exclude(status='closed').count(),
        },
        'filters': {
            'portfolio': portfolio_id or '',
            'risk_band': risk_band or '',
            'status': status or '',
            'date_from': date_from or '',
            'date_to': date_to or '',
        },
        'ordering': {
            'sort': sort,
            'direction': direction,
        },
        'portfolios': Portfolio.objects.order_by('name'),
        'status_options': status_options,
        'results_page': results_page,
        'sort_links': sort_links,
        'page_links': page_links,
        'top_risk_segments': top_risk_segments,
    }

    return render(request, 'dashboard/management_dashboard.html', context)
