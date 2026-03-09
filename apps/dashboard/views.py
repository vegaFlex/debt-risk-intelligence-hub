from decimal import Decimal

from django.db.models import Count, DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import render

from apps.portfolio.models import Debtor, Payment, Portfolio


def management_dashboard_view(request):
    portfolio_id = request.GET.get('portfolio')
    risk_band = request.GET.get('risk_band')
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

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

    debtors = debtors.order_by('-risk_score', '-outstanding_total')

    zero_decimal = Value(Decimal('0.00'), output_field=DecimalField(max_digits=14, decimal_places=2))

    total_debtors = debtors.count()
    outstanding_total = debtors.aggregate(value=Coalesce(Sum('outstanding_total'), zero_decimal))['value']
    collected_total = Payment.objects.filter(debtor__in=debtors).aggregate(
        value=Coalesce(Sum('paid_amount'), zero_decimal)
    )['value']

    contacted_statuses = ['contacted', 'promise_to_pay', 'paying', 'closed']
    contacted_count = debtors.filter(status__in=contacted_statuses).count()
    ptp_count = debtors.filter(status='promise_to_pay').count()
    paying_count = debtors.filter(status='paying').count()

    low_total = debtors.filter(risk_band='low').aggregate(value=Coalesce(Sum('outstanding_total'), zero_decimal))['value']
    medium_total = debtors.filter(risk_band='medium').aggregate(
        value=Coalesce(Sum('outstanding_total'), zero_decimal)
    )['value']
    high_total = debtors.filter(risk_band='high').aggregate(value=Coalesce(Sum('outstanding_total'), zero_decimal))['value']

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
        debtors.values('portfolio__name', 'risk_band', 'status')
        .annotate(
            debtor_count=Count('id'),
            total_outstanding=Coalesce(Sum('outstanding_total'), zero_decimal),
        )
        .order_by('-debtor_count', '-total_outstanding')[:8]
    )

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
            'open_cases': debtors.exclude(status='closed').count(),
        },
        'filters': {
            'portfolio': portfolio_id or '',
            'risk_band': risk_band or '',
            'status': status or '',
            'date_from': date_from or '',
            'date_to': date_to or '',
        },
        'portfolios': Portfolio.objects.order_by('name'),
        'top_risk_debtors': debtors[:15],
        'top_risk_segments': top_risk_segments,
    }

    return render(request, 'dashboard/management_dashboard.html', context)

