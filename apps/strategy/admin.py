from django.contrib import admin

from apps.strategy.models import (
    ActionRule,
    ActionScenario,
    CollectorQueueAssignment,
    DebtorActionRecommendation,
    StrategyRun,
    StrategyRunResult,
)


@admin.register(ActionRule)
class ActionRuleAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'recommended_action', 'risk_band', 'debtor_status', 'dpd_min', 'dpd_max', 'priority_weight', 'active',
    )
    search_fields = ('name', 'debtor_status', 'notes')
    list_filter = ('recommended_action', 'risk_band', 'active')


@admin.register(DebtorActionRecommendation)
class DebtorActionRecommendationAdmin(admin.ModelAdmin):
    list_display = (
        'debtor', 'recommended_action', 'recommended_channel', 'priority_score', 'expected_uplift_pct',
        'expected_uplift_amount', 'model_version', 'created_at',
    )
    search_fields = ('debtor__full_name', 'debtor__external_id', 'reason_summary', 'model_version')
    list_filter = ('recommended_action', 'recommended_channel', 'model_version', 'created_at')


@admin.register(ActionScenario)
class ActionScenarioAdmin(admin.ModelAdmin):
    list_display = (
        'debtor', 'action_type', 'expected_recovery_pct', 'expected_uplift_pct', 'estimated_cost', 'estimated_roi', 'created_at',
    )
    search_fields = ('debtor__full_name', 'debtor__external_id')
    list_filter = ('action_type', 'created_at')


class StrategyRunResultInline(admin.StackedInline):
    model = StrategyRunResult
    extra = 0


@admin.register(StrategyRun)
class StrategyRunAdmin(admin.ModelAdmin):
    list_display = ('name', 'portfolio', 'strategy_type', 'created_by', 'created_at')
    search_fields = ('name', 'portfolio__name', 'created_by__username', 'notes')
    list_filter = ('strategy_type', 'created_at')
    inlines = [StrategyRunResultInline]


@admin.register(CollectorQueueAssignment)
class CollectorQueueAssignmentAdmin(admin.ModelAdmin):
    list_display = ('collector_name', 'priority_rank', 'debtor', 'action_type', 'status', 'assigned_at')
    search_fields = ('collector_name', 'debtor__full_name', 'debtor__external_id')
    list_filter = ('action_type', 'status', 'assigned_at')
