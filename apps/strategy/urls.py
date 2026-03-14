from django.urls import path

from apps.strategy.views import (
    ActionRuleEditView,
    ActionRuleListView,
    CollectionsQueueView,
    CollectionsSimulatorView,
    CollectionsWorkspaceView,
)

urlpatterns = [
    path('', CollectionsWorkspaceView.as_view(), name='strategy-workspace'),
    path('queue/', CollectionsQueueView.as_view(), name='strategy-queue'),
    path('simulator/', CollectionsSimulatorView.as_view(), name='strategy-simulator'),
    path('rules/', ActionRuleListView.as_view(), name='strategy-rules'),
    path('rules/<int:rule_id>/edit/', ActionRuleEditView.as_view(), name='strategy-rule-edit'),
]
