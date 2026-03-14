from django.conf import settings
from django.db import models

from apps.portfolio.models import Debtor, Portfolio


class ActionType(models.TextChoices):
    CALL = 'call', 'Call'
    SMS = 'sms', 'SMS'
    EMAIL = 'email', 'Email'
    SETTLEMENT = 'settlement', 'Settlement Offer'
    LEGAL_REVIEW = 'legal_review', 'Legal Review'
    FIELD_VISIT = 'field_visit', 'Field Visit'
    MONITOR = 'monitor', 'Monitor'


class StrategyType(models.TextChoices):
    CALL_FIRST = 'call_first', 'Call-First'
    DIGITAL_FIRST = 'digital_first', 'Digital-First'
    SETTLEMENT_FIRST = 'settlement_first', 'Settlement-First'
    LEGAL_ESCALATION = 'legal_escalation', 'Legal Escalation'
    BALANCED = 'balanced', 'Balanced Mix'


class QueueStatus(models.TextChoices):
    QUEUED = 'queued', 'Queued'
    IN_PROGRESS = 'in_progress', 'In Progress'
    COMPLETED = 'completed', 'Completed'
    SKIPPED = 'skipped', 'Skipped'


class ActionRule(models.Model):
    name = models.CharField(max_length=160)
    risk_band = models.CharField(max_length=10, choices=Debtor.RiskBand.choices, blank=True)
    debtor_status = models.CharField(max_length=40, blank=True)
    dpd_min = models.PositiveIntegerField(default=0)
    dpd_max = models.PositiveIntegerField(default=9999)
    requires_phone = models.BooleanField(default=False)
    requires_email = models.BooleanField(default=False)
    recommended_action = models.CharField(max_length=30, choices=ActionType.choices)
    recommended_channel = models.CharField(max_length=30, choices=ActionType.choices, blank=True)
    base_uplift_pct = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    priority_weight = models.PositiveSmallIntegerField(default=50)
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name', 'id')

    def __str__(self):
        return self.name


class DebtorActionRecommendation(models.Model):
    debtor = models.ForeignKey(Debtor, on_delete=models.CASCADE, related_name='action_recommendations')
    recommended_action = models.CharField(max_length=30, choices=ActionType.choices)
    recommended_channel = models.CharField(max_length=30, choices=ActionType.choices, blank=True)
    priority_score = models.DecimalField(max_digits=6, decimal_places=2)
    expected_uplift_pct = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    expected_uplift_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    reason_summary = models.TextField(blank=True)
    model_version = models.CharField(max_length=80, default='strategy-rules-v1')
    source_rule = models.ForeignKey(ActionRule, on_delete=models.SET_NULL, null=True, blank=True, related_name='recommendations')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-priority_score', '-created_at', '-id')

    def __str__(self):
        return f'{self.debtor.full_name} -> {self.get_recommended_action_display()}'


class ActionScenario(models.Model):
    debtor = models.ForeignKey(Debtor, on_delete=models.CASCADE, related_name='action_scenarios')
    action_type = models.CharField(max_length=30, choices=ActionType.choices)
    expected_recovery_pct = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    expected_recovery_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    expected_uplift_pct = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    estimated_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    estimated_roi = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('debtor', 'action_type', '-created_at', '-id')

    def __str__(self):
        return f'{self.debtor.full_name} - {self.get_action_type_display()}'


class StrategyRun(models.Model):
    name = models.CharField(max_length=160)
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='strategy_runs')
    strategy_type = models.CharField(max_length=30, choices=StrategyType.choices)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='strategy_runs')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at', '-id')

    def __str__(self):
        return f'{self.name} ({self.portfolio.name})'


class StrategyRunResult(models.Model):
    strategy_run = models.OneToOneField(StrategyRun, on_delete=models.CASCADE, related_name='result')
    debtor_count = models.PositiveIntegerField(default=0)
    expected_total_recovery = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    expected_total_uplift = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    expected_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    expected_roi = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ('-strategy_run__created_at', '-id')

    def __str__(self):
        return f'Result - {self.strategy_run.name}'


class CollectorQueueAssignment(models.Model):
    debtor = models.ForeignKey(Debtor, on_delete=models.CASCADE, related_name='collector_queue_assignments')
    collector_name = models.CharField(max_length=120)
    priority_rank = models.PositiveIntegerField()
    action_type = models.CharField(max_length=30, choices=ActionType.choices)
    status = models.CharField(max_length=20, choices=QueueStatus.choices, default=QueueStatus.QUEUED)
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('priority_rank', '-assigned_at', '-id')
        unique_together = ('collector_name', 'priority_rank')

    def __str__(self):
        return f'{self.collector_name} #{self.priority_rank} - {self.debtor.full_name}'
