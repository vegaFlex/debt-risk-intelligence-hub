from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView

from apps.portfolio.models import Debtor, Portfolio
from apps.strategy.forms import ActionRuleForm
from apps.strategy.models import ActionRule, StrategyRun
from apps.strategy.services import (
    build_debtor_strategy_detail,
    build_collector_queue,
    build_strategy_simulator,
    format_compact_money,
    format_roi_multiple,
    build_strategy_workspace,
    save_strategy_run,
)
from apps.users.decorators import manager_or_admin_required, viewer_or_manager_or_admin_required


def _selected_portfolio(request):
    portfolio_id = request.GET.get('portfolio', '').strip()
    if not portfolio_id:
        return None
    try:
        return Portfolio.objects.get(id=portfolio_id)
    except Portfolio.DoesNotExist:
        return None


def _strategy_filter_context(request):
    return {
        'portfolios': Portfolio.objects.order_by('name'),
        'selected_portfolio': _selected_portfolio(request),
    }


@method_decorator(viewer_or_manager_or_admin_required, name='dispatch')
class CollectionsWorkspaceView(TemplateView):
    template_name = 'strategy/workspace.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filter_context = _strategy_filter_context(self.request)
        context.update(filter_context)
        context.update(build_strategy_workspace(portfolio=filter_context['selected_portfolio']))
        return context


@method_decorator(viewer_or_manager_or_admin_required, name='dispatch')
class CollectionsQueueView(TemplateView):
    template_name = 'strategy/queue.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filter_context = _strategy_filter_context(self.request)
        context.update(filter_context)
        context.update(build_collector_queue(portfolio=filter_context['selected_portfolio']))
        return context


class CollectionsSimulatorView(View):
    template_name = 'strategy/simulator.html'

    def _context(self, request):
        filter_context = _strategy_filter_context(request)
        selected_portfolio = filter_context['selected_portfolio']
        saved_runs = []
        if selected_portfolio:
            for run in StrategyRun.objects.select_related('portfolio', 'created_by', 'result').filter(portfolio=selected_portfolio)[:8]:
                run.expected_total_recovery_display = format_compact_money(run.result.expected_total_recovery)
                run.expected_total_uplift_display = format_compact_money(run.result.expected_total_uplift)
                run.expected_cost_display = format_compact_money(run.result.expected_cost)
                run.expected_roi_multiple = format_roi_multiple(run.result.expected_roi)
                saved_runs.append(run)

        context = {
            **filter_context,
            **build_strategy_simulator(portfolio=selected_portfolio),
            'can_save_runs': getattr(request.user, 'role', None) in {'manager', 'admin'},
            'can_manage_runs': getattr(request.user, 'role', None) in {'manager', 'admin'},
            'saved_runs': saved_runs,
        }
        return context

    @method_decorator(viewer_or_manager_or_admin_required)
    def get(self, request):
        return render(request, self.template_name, self._context(request))

    @method_decorator(manager_or_admin_required)
    def post(self, request):
        selected_portfolio = _selected_portfolio(request)
        action = request.POST.get('action', 'save_run').strip()

        if action == 'delete_run':
            if selected_portfolio is None:
                messages.error(request, 'Select a portfolio before deleting a saved strategy run.')
                return redirect('strategy-simulator')
            run_id = request.POST.get('run_id', '').strip()
            strategy_run = get_object_or_404(StrategyRun, id=run_id, portfolio=selected_portfolio)
            deleted_name = strategy_run.name
            strategy_run.delete()
            messages.success(request, f'Strategy run deleted: {deleted_name}.')
            return redirect(f"/strategy/simulator/?portfolio={selected_portfolio.id}")

        if selected_portfolio is None:
            messages.error(request, 'Select a portfolio before saving a strategy run.')
            return redirect('strategy-simulator')

        strategy_key = request.POST.get('strategy_key', '').strip() or None
        notes = request.POST.get('notes', '').strip()
        saved_run = save_strategy_run(
            portfolio=selected_portfolio,
            created_by=request.user,
            strategy_key=strategy_key,
            notes=notes,
        )
        if saved_run is None:
            messages.error(request, 'No strategy run could be saved for the selected portfolio.')
        else:
            messages.success(request, f'Strategy run saved: {saved_run.name}.')
        return redirect(f"/strategy/simulator/?portfolio={selected_portfolio.id}")


@method_decorator(viewer_or_manager_or_admin_required, name='dispatch')
class DebtorStrategyDetailView(TemplateView):
    template_name = 'strategy/debtor_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        debtor = get_object_or_404(Debtor, id=kwargs['debtor_id'])
        context.update(build_debtor_strategy_detail(debtor))
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
