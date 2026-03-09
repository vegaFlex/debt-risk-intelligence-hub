import io
from decimal import Decimal

from django.db.models import Count, DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from apps.portfolio.models import Debtor, Payment


def build_summary(period_start=None, period_end=None):
    debtors = Debtor.objects.select_related('portfolio').all()
    payments = Payment.objects.select_related('debtor').all()

    if period_start:
        debtors = debtors.filter(created_at__date__gte=period_start)
        payments = payments.filter(payment_date__gte=period_start)
    if period_end:
        debtors = debtors.filter(created_at__date__lte=period_end)
        payments = payments.filter(payment_date__lte=period_end)

    zero_decimal = Value(Decimal('0.00'), output_field=DecimalField(max_digits=14, decimal_places=2))

    total_debtors = debtors.count()
    outstanding_total = debtors.aggregate(value=Coalesce(Sum('outstanding_total'), zero_decimal))['value']
    collected_total = payments.aggregate(value=Coalesce(Sum('paid_amount'), zero_decimal))['value']

    contacted_statuses = ['contacted', 'promise_to_pay', 'paying', 'closed']
    contacted_count = debtors.filter(status__in=contacted_statuses).count()
    ptp_count = debtors.filter(status='promise_to_pay').count()
    paying_count = debtors.filter(status='paying').count()

    contact_rate = (contacted_count / total_debtors * 100) if total_debtors else 0
    ptp_rate = (ptp_count / contacted_count * 100) if contacted_count else 0
    conversion_rate = (paying_count / contacted_count * 100) if contacted_count else 0
    recovery_rate = (collected_total / outstanding_total * 100) if outstanding_total else 0

    top_segments = list(
        debtors.values('portfolio__name', 'risk_band', 'status')
        .annotate(
            debtor_count=Count('id'),
            total_outstanding=Coalesce(Sum('outstanding_total'), zero_decimal),
        )
        .order_by('-debtor_count', '-total_outstanding')[:10]
    )

    return {
        'kpis': {
            'total_debtors': total_debtors,
            'contact_rate': round(contact_rate, 2),
            'ptp_rate': round(ptp_rate, 2),
            'conversion_rate': round(conversion_rate, 2),
            'recovery_rate': round(float(recovery_rate), 2),
            'outstanding_total': round(float(outstanding_total), 2),
            'collected_total': round(float(collected_total), 2),
        },
        'top_segments': [
            {
                'portfolio': item['portfolio__name'],
                'risk_band': item['risk_band'],
                'status': item['status'],
                'debtor_count': item['debtor_count'],
                'total_outstanding': float(item['total_outstanding']),
            }
            for item in top_segments
        ],
    }


def build_excel_report(summary):
    wb = Workbook()
    ws_kpi = wb.active
    ws_kpi.title = 'KPI Summary'

    ws_kpi.append(['Metric', 'Value'])
    for key, value in summary['kpis'].items():
        ws_kpi.append([key, value])

    ws_seg = wb.create_sheet(title='Top Segments')
    ws_seg.append(['Portfolio', 'Risk Band', 'Status', 'Debtor Count', 'Total Outstanding'])
    for seg in summary['top_segments']:
        ws_seg.append(
            [
                seg['portfolio'],
                seg['risk_band'],
                seg['status'],
                seg['debtor_count'],
                seg['total_outstanding'],
            ]
        )

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


def build_pdf_report(summary, period_label='All Time'):
    output = io.BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    width, height = A4

    y = height - 40
    pdf.setFont('Helvetica-Bold', 14)
    pdf.drawString(40, y, 'Debt & Risk Weekly Management Report')
    y -= 20
    pdf.setFont('Helvetica', 10)
    pdf.drawString(40, y, f'Period: {period_label}')
    y -= 24

    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawString(40, y, 'KPI Summary')
    y -= 16

    pdf.setFont('Helvetica', 10)
    for key, value in summary['kpis'].items():
        pdf.drawString(50, y, f'{key}: {value}')
        y -= 14

    y -= 8
    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawString(40, y, 'Top Risk Segments')
    y -= 16

    pdf.setFont('Helvetica', 9)
    for seg in summary['top_segments'][:10]:
        line = (
            f"{seg['portfolio']} | {seg['risk_band']} | {seg['status']} | "
            f"count={seg['debtor_count']} | total={seg['total_outstanding']}"
        )
        pdf.drawString(45, y, line[:120])
        y -= 12
        if y < 50:
            pdf.showPage()
            y = height - 40
            pdf.setFont('Helvetica', 9)

    pdf.save()
    return output.getvalue()
