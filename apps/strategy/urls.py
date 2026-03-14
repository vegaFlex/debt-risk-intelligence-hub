from django.urls import path

from apps.strategy.views import (
    CollectionsQueueView,
    CollectionsSimulatorView,
    CollectionsWorkspaceView,
)

urlpatterns = [
    path('', CollectionsWorkspaceView.as_view(), name='strategy-workspace'),
    path('queue/', CollectionsQueueView.as_view(), name='strategy-queue'),
    path('simulator/', CollectionsSimulatorView.as_view(), name='strategy-simulator'),
]
