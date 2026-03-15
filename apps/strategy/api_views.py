from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.strategy.serializers import (
    CollectorQueueItemSerializer,
    CollectorQueueSummarySerializer,
    StrategyRecommendationSerializer,
    StrategyScenarioSerializer,
    StrategySimulatorSummarySerializer,
    StrategySummarySerializer,
)
from apps.strategy.services import build_collector_queue, build_strategy_simulator, build_strategy_workspace


class IsStrategyViewerOrAbove(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, 'role', None) in {'visitor', 'manager', 'admin'}
        )



class StrategyRecommendationsAPIView(APIView):
    permission_classes = [IsStrategyViewerOrAbove]

    def get(self, request):
        payload = build_strategy_workspace()
        summary = {
            'debtor_count': payload['summary']['debtor_count'],
            'top_priority_score': payload['summary']['top_priority_score'],
            'avg_priority_score': payload['summary']['avg_priority_score'],
            'expected_total_uplift': payload['summary']['expected_total_uplift'],
            'highest_value_action': payload['summary']['highest_value_action'],
        }
        rows = [
            {
                'debtor_id': item['debtor'].id,
                'debtor_name': item['debtor'].full_name,
                'portfolio_id': item['portfolio'].id,
                'portfolio_name': item['portfolio'].name,
                'status': item['debtor'].status,
                'risk_band': item['debtor'].risk_band,
                'days_past_due': item['debtor'].days_past_due,
                'recommended_action': item['recommended_action_label'],
                'recommended_channel': item['recommended_channel_label'],
                'priority_score': item['priority_score'],
                'expected_uplift_pct': item['expected_uplift_pct'],
                'expected_uplift_amount': item['expected_uplift_amount'],
                'outstanding_total': item['outstanding_total'],
                'contactability_score': item['contactability_score'],
                'reason_summary': item['reason_summary'],
            }
            for item in payload['recommendations']
        ]
        return Response({
            'summary': StrategySummarySerializer(summary).data,
            'results': StrategyRecommendationSerializer(rows, many=True).data,
        })


class StrategyCollectorQueueAPIView(APIView):
    permission_classes = [IsStrategyViewerOrAbove]

    def get(self, request):
        payload = build_collector_queue()
        summary = {
            'queued_cases': payload['queue_summary']['queued_cases'],
            'act_now_cases': payload['queue_summary']['act_now_cases'],
            'avg_priority_score': payload['queue_summary']['avg_priority_score'],
            'expected_total_uplift': payload['queue_summary']['expected_total_uplift'],
            'top_action': payload['queue_summary']['top_action'],
        }
        rows = [
            {
                'queue_rank': item['queue_rank'],
                'collector_name': item['collector_name'],
                'lane_position': item['lane_position'],
                'priority_bucket': item['priority_bucket'],
                'debtor_id': item['debtor'].id,
                'debtor_name': item['debtor'].full_name,
                'portfolio_name': item['portfolio'].name,
                'recommended_action': item['recommended_action_label'],
                'recommended_channel': item['recommended_channel_label'],
                'priority_score': item['priority_score'],
                'expected_uplift_pct': item['expected_uplift_pct'],
                'expected_uplift_amount': item['expected_uplift_amount'],
                'outstanding_total': item['outstanding_total'],
                'reason_summary': item['reason_summary'],
            }
            for item in payload['queue_rows']
        ]
        return Response({
            'summary': CollectorQueueSummarySerializer(summary).data,
            'results': CollectorQueueItemSerializer(rows, many=True).data,
        })


class StrategySimulatorAPIView(APIView):
    permission_classes = [IsStrategyViewerOrAbove]

    def get(self, request):
        payload = build_strategy_simulator()
        summary = {
            'strategy_count': payload['simulator_summary']['strategy_count'],
            'best_strategy': payload['simulator_summary']['best_strategy'],
            'best_roi': payload['simulator_summary']['best_roi'],
            'best_uplift': payload['winner']['expected_total_uplift'] if payload['winner'] else 0,
            'targeted_cases': payload['simulator_summary']['targeted_cases'],
        }
        rows = [
            {
                'key': item['key'],
                'label': item['label'],
                'description': item['description'],
                'debtor_count': item['debtor_count'],
                'expected_total_recovery': item['expected_total_recovery'],
                'expected_total_uplift': item['expected_total_uplift'],
                'expected_cost': item['expected_cost'],
                'expected_roi': item['expected_roi'],
                'avg_priority_score': item['avg_priority_score'],
                'best_fit_segments': item['best_fit_segments'],
            }
            for item in payload['strategy_rows']
        ]
        return Response({
            'summary': StrategySimulatorSummarySerializer(summary).data,
            'results': StrategyScenarioSerializer(rows, many=True).data,
        })
