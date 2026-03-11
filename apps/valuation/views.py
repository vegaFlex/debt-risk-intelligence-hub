from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.portfolio.models import Portfolio
from apps.reports.views import ManagerOrAdminRequiredMixin
from apps.valuation.services import build_rule_based_valuation, persist_rule_based_valuation


def _workspace_nav(request):
    return {
        'primary': [
            {'label': 'Valuation Workspace', 'href': '/valuation/'},
        ],
        'secondary': [
            {'label': 'High Risk Cases', 'href': '/dashboard/?risk_band=high'},
            {'label': 'PTP Cases', 'href': '/dashboard/?status=promise_to_pay'},
            {'label': 'Paying Cases', 'href': '/dashboard/?status=paying'},
            {'label': 'Open Cases', 'href': '/dashboard/?status=new'},
            {'label': 'Excel Report', 'href': '/reports/management/excel/'},
            {'label': 'PDF Report', 'href': '/reports/management/pdf/'},
            {'label': 'API Portfolios', 'href': '/api/portfolios/'},
            {'label': 'API Debtors', 'href': '/api/debtors/'},
            {'label': 'API KPIs', 'href': '/api/kpis/overview/'},
        ],
        'admin_href': '/admin/' if getattr(request.user, 'role', None) == 'admin' else None,
    }


class ValuationWorkspaceView(ManagerOrAdminRequiredMixin, View):
    def get(self, request):
        portfolios = Portfolio.objects.all().prefetch_related('valuations').order_by('-purchase_date', '-id')
        portfolio_cards = []

        for portfolio in portfolios:
            portfolio_cards.append(
                {
                    'portfolio': portfolio,
                    'latest_valuation': portfolio.valuations.first(),
                    'preview': build_rule_based_valuation(portfolio),
                }
            )

        return render(
            request,
            'valuation/portfolio_list.html',
            {
                'portfolio_cards': portfolio_cards,
                'nav_actions': _workspace_nav(request),
            },
        )


class PortfolioValuationPreviewView(ManagerOrAdminRequiredMixin, View):
    def get(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio.objects.prefetch_related('valuations__factors'), id=portfolio_id)
        latest_valuation = portfolio.valuations.first()

        return render(
            request,
            'valuation/preview.html',
            {
                'portfolio': portfolio,
                'preview': build_rule_based_valuation(portfolio),
                'latest_valuation': latest_valuation,
                'latest_factors': latest_valuation.factors.all()[:8] if latest_valuation else [],
                'nav_actions': _workspace_nav(request),
            },
        )


class RunPortfolioValuationView(ManagerOrAdminRequiredMixin, View):
    def post(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio.objects.prefetch_related('valuations'), id=portfolio_id)
        latest_valuation = portfolio.valuations.first()

        valuation = persist_rule_based_valuation(
            portfolio,
            creditor=latest_valuation.creditor if latest_valuation else None,
            upload_batch=latest_valuation.upload_batch if latest_valuation else None,
            created_by=request.user,
        )

        messages.success(
            request,
            f'Rule-based valuation saved for {portfolio.name}. Recommended bid: {valuation.recommended_bid_pct}% of face value.',
        )
        return redirect('valuation-preview', portfolio_id=portfolio.id)
