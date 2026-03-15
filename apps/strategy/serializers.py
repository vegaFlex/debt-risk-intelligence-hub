from rest_framework import serializers


class StrategyRecommendationSerializer(serializers.Serializer):
    debtor_id = serializers.IntegerField()
    debtor_name = serializers.CharField()
    portfolio_id = serializers.IntegerField()
    portfolio_name = serializers.CharField()
    status = serializers.CharField()
    risk_band = serializers.CharField()
    days_past_due = serializers.IntegerField()
    recommended_action = serializers.CharField()
    recommended_channel = serializers.CharField()
    priority_score = serializers.DecimalField(max_digits=6, decimal_places=2)
    expected_uplift_pct = serializers.DecimalField(max_digits=6, decimal_places=2)
    expected_uplift_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    outstanding_total = serializers.DecimalField(max_digits=14, decimal_places=2)
    contactability_score = serializers.DecimalField(max_digits=6, decimal_places=2)
    reason_summary = serializers.CharField()


class StrategySummarySerializer(serializers.Serializer):
    debtor_count = serializers.IntegerField()
    top_priority_score = serializers.DecimalField(max_digits=6, decimal_places=2)
    avg_priority_score = serializers.DecimalField(max_digits=6, decimal_places=2)
    expected_total_uplift = serializers.DecimalField(max_digits=14, decimal_places=2)
    highest_value_action = serializers.CharField()


class CollectorQueueItemSerializer(serializers.Serializer):
    queue_rank = serializers.IntegerField()
    collector_name = serializers.CharField()
    lane_position = serializers.IntegerField()
    priority_bucket = serializers.CharField()
    debtor_id = serializers.IntegerField()
    debtor_name = serializers.CharField()
    portfolio_name = serializers.CharField()
    recommended_action = serializers.CharField()
    recommended_channel = serializers.CharField()
    priority_score = serializers.DecimalField(max_digits=6, decimal_places=2)
    expected_uplift_pct = serializers.DecimalField(max_digits=6, decimal_places=2)
    expected_uplift_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    outstanding_total = serializers.DecimalField(max_digits=14, decimal_places=2)
    reason_summary = serializers.CharField()


class CollectorQueueSummarySerializer(serializers.Serializer):
    queued_cases = serializers.IntegerField()
    act_now_cases = serializers.IntegerField()
    avg_priority_score = serializers.DecimalField(max_digits=6, decimal_places=2)
    expected_total_uplift = serializers.DecimalField(max_digits=14, decimal_places=2)
    top_action = serializers.CharField()


class StrategyScenarioSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField()
    debtor_count = serializers.IntegerField()
    expected_total_recovery = serializers.DecimalField(max_digits=14, decimal_places=2)
    expected_total_uplift = serializers.DecimalField(max_digits=14, decimal_places=2)
    expected_cost = serializers.DecimalField(max_digits=14, decimal_places=2)
    expected_roi = serializers.DecimalField(max_digits=8, decimal_places=2)
    avg_priority_score = serializers.DecimalField(max_digits=6, decimal_places=2)
    best_fit_segments = serializers.ListField(child=serializers.CharField())


class StrategySimulatorSummarySerializer(serializers.Serializer):
    strategy_count = serializers.IntegerField()
    best_strategy = serializers.CharField()
    best_roi = serializers.DecimalField(max_digits=8, decimal_places=2)
    best_uplift = serializers.DecimalField(max_digits=14, decimal_places=2)
    targeted_cases = serializers.IntegerField()
