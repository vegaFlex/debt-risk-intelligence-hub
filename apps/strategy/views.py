from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView

from apps.strategy.forms import ActionRuleForm
from apps.strategy.models import ActionRule
from apps.strategy.services import build_collector_queue, build_strategy_simulator, build_strategy_workspace
from apps.users.decorators import manager_or_admin_required, viewer_or_manager_or_admin_required


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_strategy_simulator())
        return context


class ActionRuleListView(View):
    @method_decorator(viewer_or_manager_or_admin_required)
    def get(self, request):
        selected_action = request.GET.get('action', '')
        rules = ActionRule.objects.all().order_by('name', 'id')
        if selected_action:
            rules = rules.filter(recommended_action=selected_action)

        return render(
            request,
            'strategy/rules.html',
            {
                'rules': rules,
                'form': ActionRuleForm(),
                'editing_rule': None,
                'selected_action': selected_action,
                'action_choices': ActionRule._meta.get_field('recommended_action').choices,
                'can_manage_rules': getattr(request.user, 'role', None) in {'manager', 'admin'},
            },
        )

    @method_decorator(manager_or_admin_required)
    def post(self, request):
        form = ActionRuleForm(request.POST)
        selected_action = request.GET.get('action', '')
        if form.is_valid():
            rule = form.save()
            messages.success(request, f'Action rule saved: {rule.name}.')
            return redirect('strategy-rules')

        rules = ActionRule.objects.all().order_by('name', 'id')
        if selected_action:
            rules = rules.filter(recommended_action=selected_action)
        return render(
            request,
            'strategy/rules.html',
            {
                'rules': rules,
                'form': form,
                'editing_rule': None,
                'selected_action': selected_action,
                'action_choices': ActionRule._meta.get_field('recommended_action').choices,
                'can_manage_rules': True,
            },
        )


class ActionRuleEditView(View):
    @method_decorator(manager_or_admin_required)
    def get(self, request, rule_id):
        rule = get_object_or_404(ActionRule, id=rule_id)
        rules = ActionRule.objects.all().order_by('name', 'id')
        return render(
            request,
            'strategy/rules.html',
            {
                'rules': rules,
                'form': ActionRuleForm(instance=rule),
                'editing_rule': rule,
                'selected_action': '',
                'action_choices': ActionRule._meta.get_field('recommended_action').choices,
                'can_manage_rules': True,
            },
        )

    @method_decorator(manager_or_admin_required)
    def post(self, request, rule_id):
        rule = get_object_or_404(ActionRule, id=rule_id)
        form = ActionRuleForm(request.POST, instance=rule)
        if form.is_valid():
            saved = form.save()
            messages.success(request, f'Action rule updated: {saved.name}.')
            return redirect('strategy-rules')

        rules = ActionRule.objects.all().order_by('name', 'id')
        return render(
            request,
            'strategy/rules.html',
            {
                'rules': rules,
                'form': form,
                'editing_rule': rule,
                'selected_action': '',
                'action_choices': ActionRule._meta.get_field('recommended_action').choices,
                'can_manage_rules': True,
            },
        )
