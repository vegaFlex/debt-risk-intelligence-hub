from rest_framework import serializers

from apps.portfolio.models import Debtor, Portfolio


class PortfolioSerializer(serializers.ModelSerializer):
    debtors_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Portfolio
        fields = (
            'id',
            'name',
            'source_company',
            'purchase_date',
            'purchase_price',
            'face_value',
            'currency',
            'debtors_count',
            'created_at',
        )


class DebtorSerializer(serializers.ModelSerializer):
    portfolio_name = serializers.CharField(source='portfolio.name', read_only=True)

    class Meta:
        model = Debtor
        fields = (
            'id',
            'portfolio',
            'portfolio_name',
            'external_id',
            'full_name',
            'status',
            'days_past_due',
            'outstanding_principal',
            'outstanding_total',
            'risk_score',
            'risk_band',
            'risk_factors',
            'created_at',
        )


class DebtorRiskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Debtor
        fields = ('id', 'external_id', 'full_name', 'risk_score', 'risk_band', 'risk_factors', 'updated_at')
