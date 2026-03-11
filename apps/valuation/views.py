from decimal import Decimal

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


def _round_score(value):
    return Decimal(value).quantize(Decimal('0.01'))


def _attractiveness_score(preview):
    score = Decimal('0.00')
    score += Decimal(preview['expected_recovery_rate']) * Decimal('0.40')
    score += Decimal(preview['projected_roi']) * Decimal('0.30')
    score += Decimal(preview['confidence_score']) * Decimal('0.20')
    score += Decimal(preview['stats']['paying_share']) * Decimal('0.10')
    score -= Decimal(preview['stats']['high_risk_share']) * Decimal('0.12')
    return max(Decimal('0.00'), _round_score(score))


def _portfolio_signal_label(score):
    if score >= Decimal('45.00'):
        return 'Strong Buy Zone'
    if score >= Decimal('32.00'):
        return 'Review Closely'
    return 'Watchlist'


class ValuationWorkspaceView(ManagerOrAdminRequiredMixin, View):
    def get(self, request):
        portfolios = Portfolio.objects.all().prefetch_related('valuations').order_by('-purchase_date', '-id')
        portfolio_cards = []

        for portfolio in portfolios:
            preview = build_rule_based_valuation(portfolio)
            attractiveness_score = _attractiveness_score(preview)
            portfolio_cards.append(
                {
                    'portfolio': portfolio,
                    'latest_valuation': portfolio.valuations.first(),
                    'preview': preview,
                    'attractiveness_score': attractiveness_score,
                    'signal_label': _portfolio_signal_label(attractiveness_score),
                }
            )

        portfolio_cards.sort(key=lambda item: item['attractiveness_score'], reverse=True)

        top_score = portfolio_cards[0]['attractiveness_score'] if portfolio_cards else Decimal('0.00')
        avg_recovery = Decimal('0.00')
        avg_confidence = Decimal('0.00')
        total_face_value = Decimal('0.00')
        if portfolio_cards:
            avg_recovery = _round_score(sum(Decimal(item['preview']['expected_recovery_rate']) for item in portfolio_cards) / len(portfolio_cards))
            avg_confidence = _round_score(sum(Decimal(item['preview']['confidence_score']) for item in portfolio_cards) / len(portfolio_cards))
            total_face_value = sum(Decimal(item['portfolio'].face_value) for item in portfolio_cards)

        summary = {
            'portfolio_count': len(portfolio_cards),
            'top_score': top_score,
            'avg_recovery': avg_recovery,
            'avg_confidence': avg_confidence,
            'total_face_value': total_face_value.quantize(Decimal('0.01')) if portfolio_cards else Decimal('0.00'),
        }

        return render(
            request,
            'valuation/portfolio_list.html',
            {
                'portfolio_cards': portfolio_cards,
                'summary': summary,
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
