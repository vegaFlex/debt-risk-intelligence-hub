from django.contrib import admin

from apps.valuation.models import (
    Creditor,
    HistoricalBenchmark,
    ModelPredictionLog,
    PortfolioUploadBatch,
    PortfolioValuation,
    ValuationFactor,
)


@admin.register(Creditor)
class CreditorAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'country', 'created_at')
    search_fields = ('name', 'country')
    list_filter = ('category', 'country')


@admin.register(PortfolioUploadBatch)
class PortfolioUploadBatchAdmin(admin.ModelAdmin):
    list_display = ('name', 'creditor', 'portfolio', 'reporting_currency', 'source_file_name', 'created_at')
    search_fields = ('name', 'source_file_name', 'creditor__name', 'portfolio__name')
    list_filter = ('reporting_currency', 'created_at')


class ValuationFactorInline(admin.TabularInline):
    model = ValuationFactor
    extra = 0


@admin.register(PortfolioValuation)
class PortfolioValuationAdmin(admin.ModelAdmin):
    list_display = (
        'portfolio',
        'valuation_method',
        'expected_recovery_rate',
        'recommended_bid_pct',
        'recommended_bid_amount',
        'projected_roi',
        'confidence_score',
        'created_at',
    )
    search_fields = ('portfolio__name', 'creditor__name')
    list_filter = ('valuation_method', 'created_at')
    inlines = [ValuationFactorInline]


@admin.register(HistoricalBenchmark)
class HistoricalBenchmarkAdmin(admin.ModelAdmin):
    list_display = (
        'creditor',
        'creditor_category',
        'product_type',
        'dpd_band',
        'balance_band',
        'avg_recovery_rate',
        'sample_size',
    )
    search_fields = ('creditor__name', 'product_type', 'dpd_band', 'balance_band', 'region')
    list_filter = ('creditor_category', 'product_type', 'region')


@admin.register(ModelPredictionLog)
class ModelPredictionLogAdmin(admin.ModelAdmin):
    list_display = ('portfolio', 'prediction_type', 'prediction_value', 'confidence', 'model_version', 'created_at')
    search_fields = ('portfolio__name', 'model_version')
    list_filter = ('prediction_type', 'model_version', 'created_at')
