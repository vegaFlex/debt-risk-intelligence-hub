from decimal import Decimal

from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import generics
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.portfolio.models import Debtor, Payment, Portfolio
from apps.portfolio.serializers import DebtorRiskSerializer, DebtorSerializer, PortfolioSerializer


class PortfolioListAPIView(generics.ListAPIView):
    serializer_class = PortfolioSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    ordering_fields = ['purchase_date', 'purchase_price', 'face_value', 'created_at']
    ordering = ['-purchase_date']

    def get_queryset(self):
        queryset = Portfolio.objects.annotate(debtors_count=Count('debtors')).order_by('-purchase_date', '-id')

        source_company = self.request.query_params.get('source_company')
        if source_company:
            queryset = queryset.filter(source_company__icontains=source_company)

        ordering = self.request.query_params.get('ordering')
        if ordering:
            queryset = queryset.order_by(ordering)

        return queryset


class DebtorListAPIView(generics.ListAPIView):
    serializer_class = DebtorSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Debtor.objects.select_related('portfolio').all()

        portfolio_id = self.request.query_params.get('portfolio')
        status = self.request.query_params.get('status')
        risk_band = self.request.query_params.get('risk_band')
        search = self.request.query_params.get('search')
        min_score = self.request.query_params.get('min_score')
        max_score = self.request.query_params.get('max_score')
        ordering = self.request.query_params.get('ordering', '-risk_score')

        if portfolio_id:
            queryset = queryset.filter(portfolio_id=portfolio_id)
        if status:
            queryset = queryset.filter(status=status)
        if risk_band:
            queryset = queryset.filter(risk_band=risk_band)
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search)
                | Q(external_id__icontains=search)
                | Q(phone_number__icontains=search)
            )
        if min_score:
            queryset = queryset.filter(risk_score__gte=min_score)
        if max_score:
            queryset = queryset.filter(risk_score__lte=max_score)

        allowed_ordering = {
            'risk_score',
            '-risk_score',
            'days_past_due',
            '-days_past_due',
            'outstanding_total',
            '-outstanding_total',
            'created_at',
            '-created_at',
        }
        if ordering in allowed_ordering:
            queryset = queryset.order_by(ordering)

        return queryset


class DebtorRiskDetailAPIView(generics.RetrieveAPIView):
    queryset = Debtor.objects.all()
    serializer_class = DebtorRiskSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class KpiOverviewAPIView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        debtors = Debtor.objects.all()
        total_debtors = debtors.count()

        zero_decimal = Value(Decimal('0.00'), output_field=DecimalField(max_digits=14, decimal_places=2))
        outstanding_total = debtors.aggregate(value=Coalesce(Sum('outstanding_total'), zero_decimal))['value']
        collected_total = Payment.objects.aggregate(value=Coalesce(Sum('paid_amount'), zero_decimal))['value']

        contacted_statuses = ['contacted', 'promise_to_pay', 'paying', 'closed']
        contacted_count = debtors.filter(status__in=contacted_statuses).count()
        ptp_count = debtors.filter(status='promise_to_pay').count()

        low_total = debtors.filter(risk_band='low').aggregate(value=Coalesce(Sum('outstanding_total'), zero_decimal))['value']
        medium_total = debtors.filter(risk_band='medium').aggregate(value=Coalesce(Sum('outstanding_total'), zero_decimal))['value']
        high_total = debtors.filter(risk_band='high').aggregate(value=Coalesce(Sum('outstanding_total'), zero_decimal))['value']

        weighted_expected = (
            (low_total * Decimal('0.65'))
            + (medium_total * Decimal('0.40'))
            + (high_total * Decimal('0.20'))
        )

        contact_rate = (contacted_count / total_debtors * 100) if total_debtors else 0
        ptp_rate = (ptp_count / contacted_count * 100) if contacted_count else 0
        recovery_rate = (collected_total / outstanding_total * 100) if outstanding_total else 0

        return Response(
            {
                'total_debtors': total_debtors,
                'contacted_debtors': contacted_count,
                'promise_to_pay_debtors': ptp_count,
                'contact_rate': round(contact_rate, 2),
                'ptp_rate': round(ptp_rate, 2),
                'recovery_rate': round(float(recovery_rate), 2),
                'expected_collections': round(float(weighted_expected), 2),
                'outstanding_total': float(outstanding_total),
                'collected_total': float(collected_total),
            }
        )
