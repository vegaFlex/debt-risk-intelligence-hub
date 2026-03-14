from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from apps.users.decorators import viewer_or_manager_or_admin_required


@method_decorator(viewer_or_manager_or_admin_required, name='dispatch')
class CollectionsWorkspaceView(TemplateView):
    template_name = 'strategy/workspace.html'


@method_decorator(viewer_or_manager_or_admin_required, name='dispatch')
class CollectionsQueueView(TemplateView):
    template_name = 'strategy/queue.html'


@method_decorator(viewer_or_manager_or_admin_required, name='dispatch')
class CollectionsSimulatorView(TemplateView):
    template_name = 'strategy/simulator.html'
