from django.conf import settings
from django.db import models

from apps.portfolio.models import Portfolio


class Creditor(models.Model):
    class Category(models.TextChoices):
        BANK = 'bank', 'Bank'
        FINTECH = 'fintech', 'Fintech'
        TELECOM = 'telecom', 'Telecom'
        UTILITIES = 'utilities', 'Utilities'
        RETAIL = 'retail', 'Retail'
        SME = 'sme', 'SME'
        OTHER = 'other', 'Other'

    name = models.CharField(max_length=255, unique=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    country = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class PortfolioUploadBatch(models.Model):
    name = models.CharField(max_length=255)
    creditor = models.ForeignKey(
        Creditor,
        on_delete=models.SET_NULL,
        related_name='upload_batches',
        null=True,
        blank=True,
    )
    portfolio = models.OneToOneField(
        Portfolio,
        on_delete=models.SET_NULL,
        related_name='valuation_batch',
        null=True,
        blank=True,
    )
    reporting_currency = models.CharField(max_length=3, default='EUR')
    source_file_name = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='valuation_batches',
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at', '-id')

    def __str__(self):
        return self.name


class PortfolioValuation(models.Model):
    class ValuationMethod(models.TextChoices):
        RULE_BASED = 'rule_based', 'Rule Based'
        BENCHMARK = 'benchmark', 'Benchmark'
        HYBRID = 'hybrid', 'Hybrid'
        ML = 'ml', 'ML'

    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name='valuations',
    )
    creditor = models.ForeignKey(
        Creditor,
        on_delete=models.SET_NULL,
        related_name='valuations',
        null=True,
        blank=True,
    )
    upload_batch = models.ForeignKey(
        PortfolioUploadBatch,
        on_delete=models.SET_NULL,
        related_name='valuations',
        null=True,
        blank=True,
    )
    face_value = models.DecimalField(max_digits=14, decimal_places=2)
    expected_recovery_rate = models.DecimalField(max_digits=6, decimal_places=2)
    expected_collections = models.DecimalField(max_digits=14, decimal_places=2)
    recommended_bid_pct = models.DecimalField(max_digits=6, decimal_places=2)
    recommended_bid_amount = models.DecimalField(max_digits=14, decimal_places=2)
    projected_roi = models.DecimalField(max_digits=7, decimal_places=2)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2)
    valuation_method = models.CharField(max_length=20, choices=ValuationMethod.choices, default=ValuationMethod.RULE_BASED)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='portfolio_valuations',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at', '-id')

    def __str__(self):
        return f'{self.portfolio.name} - {self.valuation_method}'


class ValuationFactor(models.Model):
    valuation = models.ForeignKey(
        PortfolioValuation,
        on_delete=models.CASCADE,
        related_name='factors',
    )
    factor_name = models.CharField(max_length=100)
    factor_weight = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    factor_value = models.CharField(max_length=255, blank=True)
    explanation = models.TextField(blank=True)

    class Meta:
        ordering = ('-factor_weight', 'factor_name')

    def __str__(self):
        return f'{self.factor_name} ({self.factor_weight})'


class HistoricalBenchmark(models.Model):
    creditor = models.ForeignKey(
        Creditor,
        on_delete=models.SET_NULL,
        related_name='benchmarks',
        null=True,
        blank=True,
    )
    creditor_category = models.CharField(max_length=20, choices=Creditor.Category.choices, default=Creditor.Category.OTHER)
    product_type = models.CharField(max_length=100, blank=True)
    dpd_band = models.CharField(max_length=50)
    balance_band = models.CharField(max_length=50)
    region = models.CharField(max_length=100, blank=True)
    avg_recovery_rate = models.DecimalField(max_digits=6, decimal_places=2)
    avg_contact_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    avg_ptp_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    avg_conversion_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    sample_size = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-sample_size', '-avg_recovery_rate')

    def __str__(self):
        creditor_label = self.creditor.name if self.creditor else self.creditor_category
        return f'{creditor_label} | {self.product_type or "General"}'


class ModelPredictionLog(models.Model):
    class PredictionType(models.TextChoices):
        RECOVERY_RATE = 'recovery_rate', 'Recovery Rate'
        EXPECTED_COLLECTIONS = 'expected_collections', 'Expected Collections'
        BID_PCT = 'bid_pct', 'Bid Percentage'
        ROI = 'roi', 'ROI'

    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name='prediction_logs',
    )
    valuation = models.ForeignKey(
        PortfolioValuation,
        on_delete=models.SET_NULL,
        related_name='prediction_logs',
        null=True,
        blank=True,
    )
    model_version = models.CharField(max_length=50)
    prediction_type = models.CharField(max_length=30, choices=PredictionType.choices)
    prediction_value = models.DecimalField(max_digits=14, decimal_places=4)
    confidence = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at', '-id')

    def __str__(self):
        return f'{self.portfolio.name} - {self.prediction_type}'
