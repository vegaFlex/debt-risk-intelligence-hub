from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from apps.strategy.services import build_collector_queue, build_strategy_workspace
from apps.users.decorators import viewer_or_manager_or_admin_required


@method_decorator(viewer_or_manager_or_admin_required, name='dispatch')
class CollectionsWorkspaceView(TemplateView):
    template_name = 'strategy/workspace.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_strategy_workspace())
        return context


@method_decorator(viewer_or_manager_or_admin_required, name='dispatch')
class CollectionsQueueView(TemplateView):
    template_name = 'strategy/queue.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_collector_queue())
        return context


@method_decorator(viewer_or_manager_or_admin_required, name='dispatch')
class CollectionsSimulatorView(TemplateView):
    template_name = 'strategy/simulator.html'
