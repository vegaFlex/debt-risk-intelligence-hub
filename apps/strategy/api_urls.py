from django.urls import path

from apps.strategy.api_views import (
    StrategyCollectorQueueAPIView,
    StrategyRecommendationsAPIView,
    StrategySimulatorAPIView,
)

urlpatterns = [
    path('recommendations/', StrategyRecommendationsAPIView.as_view(), name='api-strategy-recommendations'),
    path('queue/', StrategyCollectorQueueAPIView.as_view(), name='api-strategy-queue'),
    path('simulator/', StrategySimulatorAPIView.as_view(), name='api-strategy-simulator'),
]
