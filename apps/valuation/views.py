from decimal import Decimal

from datetime import date

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.portfolio.importers import ImportValidationError, parse_uploaded_file, validate_rows
from apps.portfolio.models import DataImportLog, Debtor, Portfolio
from apps.reports.models import GeneratedReport
from apps.reports.views import ManagerOrAdminRequiredMixin, ViewerOrManagerOrAdminReadOnlyMixin
from apps.scoring.services import calculate_risk_profile
from apps.valuation.forms import HistoricalBenchmarkForm, ValuationImportForm
from apps.valuation.models import Creditor, HistoricalBenchmark, PortfolioUploadBatch
from apps.valuation.reporting import build_valuation_excel_report, build_valuation_pdf_report, build_valuation_report_summary
from apps.valuation.services import build_rule_based_valuation, persist_rule_based_valuation


VALUATION_IMPORT_SESSION_KEY = 'valuation_import_payload'


def _workspace_nav(request):
    nav = {
        'primary': [],
        'secondary': [
            {'label': 'High Risk Cases', 'href': '/dashboard/?risk_band=high'},
            {'label': 'PTP Cases', 'href': '/dashboard/?status=promise_to_pay'},
            {'label': 'Paying Cases', 'href': '/dashboard/?status=paying'},
            {'label': 'Open Cases', 'href': '/dashboard/?status=new'},
            {'label': 'API Portfolios', 'href': '/api/portfolios/'},
            {'label': 'API Debtors', 'href': '/api/debtors/'},
            {'label': 'API KPIs', 'href': '/api/kpis/overview/'},
        ],
        'admin_href': '/admin/' if getattr(request.user, 'role', None) == 'admin' else None,
    }

    if getattr(request.user, 'role', None) in {'manager', 'admin'}:
        nav['secondary'][4:4] = [
            {'label': 'Excel Report', 'href': '/reports/management/excel/'},
            {'label': 'PDF Report', 'href': '/reports/management/pdf/'},
        ]

    return nav


def _round_score(value):
    return Decimal(value).quantize(Decimal('0.01'))


def _format_compact_money(value):
    numeric = float(value or 0)
    absolute = abs(numeric)
    if absolute >= 1_000_000:
        return f"{numeric / 1_000_000:.2f}M"
    if absolute >= 1_000:
        return f"{numeric / 1_000:.1f}K"
    return f"{numeric:.2f}"


def _decorate_preview(preview, portfolio):
    stats = dict(preview['stats'])
    stats['outstanding_total_display'] = _format_compact_money(stats['outstanding_total'])
    ml_baseline = dict(preview['ml_baseline']) if preview.get('ml_baseline') else None
    if ml_baseline:
        ml_baseline['predicted_collections_display'] = _format_compact_money(ml_baseline['predicted_collections'])
        ml_baseline['predicted_bid_amount_display'] = _format_compact_money(ml_baseline['predicted_bid_amount'])
    scenarios = []
    for scenario in preview.get('scenarios', []):
        scenarios.append({
            **scenario,
            'bid_amount_display': _format_compact_money(scenario['bid_amount']),
            'expected_profit_display': _format_compact_money(scenario['expected_profit']),
        })
    return {
        **preview,
        'expected_collections_display': _format_compact_money(preview['expected_collections']),
        'recommended_bid_amount_display': _format_compact_money(preview['recommended_bid_amount']),
        'face_value_display': _format_compact_money(portfolio.face_value),
        'stats': stats,
        'ml_baseline': ml_baseline,
        'scenarios': scenarios,
    }


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


VALUATION_SORT_OPTIONS = [
    ('attractiveness_desc', 'Attractiveness'),
    ('recovery_desc', 'Expected Recovery'),
    ('bid_desc', 'Recommended Bid'),
    ('roi_desc', 'Projected ROI'),
    ('confidence_desc', 'Confidence'),
    ('face_value_desc', 'Face Value'),
]


FILTER_SIGNAL_OPTIONS = [
    ('', 'All signals'),
    ('Strong Buy Zone', 'Strong Buy Zone'),
    ('Review Closely', 'Review Closely'),
    ('Watchlist', 'Watchlist'),
]


FILTER_RECOMMENDATION_OPTIONS = [
    ('', 'All recommendations'),
    ('Bid', 'Bid'),
    ('Hold', 'Hold'),
    ('Reject', 'Reject'),
]


FILTER_MODE_OPTIONS = [
    ('', 'All modes'),
    ('Hybrid', 'Hybrid'),
    ('Rule-Based', 'Rule-Based'),
]


DEFAULT_SORT = 'attractiveness_desc'


def _portfolio_mode_label(preview):
    return 'Hybrid' if preview['benchmark_context'] else 'Rule-Based'


def _sort_portfolio_cards(portfolio_cards, sort_by):
    sort_map = {
        'attractiveness_desc': lambda item: item['attractiveness_score'],
        'recovery_desc': lambda item: Decimal(item['preview']['expected_recovery_rate']),
        'bid_desc': lambda item: Decimal(item['preview']['recommended_bid_pct']),
        'roi_desc': lambda item: Decimal(item['preview']['projected_roi']),
        'confidence_desc': lambda item: Decimal(item['preview']['confidence_score']),
        'face_value_desc': lambda item: Decimal(item['portfolio'].face_value),
    }
    selected_sort = sort_by if sort_by in sort_map else DEFAULT_SORT
    portfolio_cards.sort(key=sort_map[selected_sort], reverse=True)
    return selected_sort


def _recommended_action(preview, attractiveness_score):
    confidence = Decimal(preview['confidence_score'])
    roi = Decimal(preview['projected_roi'])
    recovery = Decimal(preview['expected_recovery_rate'])
    high_risk = Decimal(preview['stats']['high_risk_share'])
    contactability = Decimal(preview['stats']['contactability_share'])

    if attractiveness_score >= Decimal('46.00') and roi >= Decimal('160.00') and confidence >= Decimal('55.00'):
        return {
            'label': 'Bid',
            'tone': 'strong',
            'reason': 'Recovery, ROI, and confidence are strong enough to support an active bid.',
        }

    if high_risk >= Decimal('55.00') and contactability < Decimal('45.00'):
        return {
            'label': 'Reject',
            'tone': 'danger',
            'reason': 'High-risk concentration is too heavy relative to operational reach.',
        }

    if roi < Decimal('90.00') or recovery < Decimal('18.00'):
        return {
            'label': 'Reject',
            'tone': 'danger',
            'reason': 'Projected return is too weak for a disciplined acquisition bid.',
        }

    return {
        'label': 'Hold',
        'tone': 'review',
        'reason': 'The portfolio is investable only after closer review of assumptions and segments.',
    }


def _attach_risk_profile(rows):
    scored_rows = []
    for row in rows:
        risk = calculate_risk_profile(
            days_past_due=row['days_past_due'],
            outstanding_total=row['outstanding_total'],
            status=row['status'],
        )
        scored_rows.append(
            {
                **row,
                'risk_score': risk['risk_score'],
                'risk_band': risk['risk_band'],
                'risk_factors': ' | '.join(risk['reason_factors']),
            }
        )
    return scored_rows


def _resolve_creditor(form):
    existing_creditor = form.cleaned_data.get('existing_creditor')
    if existing_creditor:
        return existing_creditor

    creditor_name = form.cleaned_data.get('creditor_name', '').strip()
    creditor_category = form.cleaned_data.get('creditor_category') or Creditor.Category.OTHER
    creditor, _ = Creditor.objects.get_or_create(
        name=creditor_name,
        defaults={'category': creditor_category},
    )
    if creditor.category != creditor_category and creditor_name:
        creditor.category = creditor_category
        creditor.save(update_fields=['category'])
    return creditor


def _build_portfolio(form, user):
    return Portfolio.objects.create(
        name=form.cleaned_data['portfolio_name'],
        source_company=form.cleaned_data['source_company'],
        purchase_date=form.cleaned_data['purchase_date'],
        purchase_price=form.cleaned_data['purchase_price'],
        face_value=form.cleaned_data['face_value'],
        currency=form.cleaned_data['currency'],
        created_by=user if user.is_authenticated else None,
    )


def _portfolio_card_payload(portfolio):
    preview = _decorate_preview(build_rule_based_valuation(portfolio), portfolio)
    attractiveness_score = _attractiveness_score(preview)
    signal_label = _portfolio_signal_label(attractiveness_score)
    recommended_action = _recommended_action(preview, attractiveness_score)
    mode_label = _portfolio_mode_label(preview)
    return {
        'portfolio': portfolio,
        'latest_valuation': portfolio.valuations.first(),
        'preview': preview,
        'attractiveness_score': attractiveness_score,
        'signal_label': signal_label,
        'recommended_action': recommended_action,
        'mode_label': mode_label,
    }


def _comparison_delta(left, right):
    return _round_score(Decimal(left) - Decimal(right))


class HistoricalBenchmarkListView(ViewerOrManagerOrAdminReadOnlyMixin, View):
    def get(self, request):
        selected_category = request.GET.get('category', '')
        benchmarks = HistoricalBenchmark.objects.select_related('creditor').order_by('-sample_size', '-avg_recovery_rate')
        if selected_category:
            benchmarks = benchmarks.filter(creditor_category=selected_category)

        return render(
            request,
            'valuation/benchmarks.html',
            {
                'benchmarks': benchmarks[:50],
                'form': HistoricalBenchmarkForm(),
                'selected_category': selected_category,
                'category_choices': Creditor.Category.choices,
                'editing_benchmark': None,
                'can_manage_benchmarks': getattr(request.user, 'role', None) in {'manager', 'admin'},
                'nav_actions': _workspace_nav(request),
                'can_export_reports': getattr(request.user, 'role', None) in {'manager', 'admin'},
            },
        )

    def post(self, request):
        form = HistoricalBenchmarkForm(request.POST)
        selected_category = request.GET.get('category', '')
        if form.is_valid():
            benchmark = form.save()
            messages.success(request, f'Benchmark saved for {benchmark.creditor or benchmark.creditor_category}.')
            return redirect('valuation-benchmarks')

        benchmarks = HistoricalBenchmark.objects.select_related('creditor').order_by('-sample_size', '-avg_recovery_rate')[:50]
        return render(
            request,
            'valuation/benchmarks.html',
            {
                'benchmarks': benchmarks,
                'form': form,
                'selected_category': selected_category,
                'category_choices': Creditor.Category.choices,
                'editing_benchmark': None,
                'can_manage_benchmarks': getattr(request.user, 'role', None) in {'manager', 'admin'},
                'nav_actions': _workspace_nav(request),
                'can_run_valuation': getattr(request.user, 'role', None) in {'manager', 'admin'},
                'can_export_reports': getattr(request.user, 'role', None) in {'manager', 'admin'},
            },
        )


class HistoricalBenchmarkEditView(ManagerOrAdminRequiredMixin, View):
    def get(self, request, benchmark_id):
        benchmark = get_object_or_404(HistoricalBenchmark.objects.select_related('creditor'), id=benchmark_id)
        benchmarks = HistoricalBenchmark.objects.select_related('creditor').order_by('-sample_size', '-avg_recovery_rate')[:50]
        return render(
            request,
            'valuation/benchmarks.html',
            {
                'benchmarks': benchmarks,
                'form': HistoricalBenchmarkForm(instance=benchmark),
                'selected_category': '',
                'category_choices': Creditor.Category.choices,
                'editing_benchmark': benchmark,
                'can_manage_benchmarks': True,
                'nav_actions': _workspace_nav(request),
            },
        )

    def post(self, request, benchmark_id):
        benchmark = get_object_or_404(HistoricalBenchmark.objects.select_related('creditor'), id=benchmark_id)
        form = HistoricalBenchmarkForm(request.POST, instance=benchmark)
        if form.is_valid():
            saved = form.save()
            messages.success(request, f'Benchmark updated for {saved.creditor or saved.creditor_category}.')
            return redirect('valuation-benchmarks')

        benchmarks = HistoricalBenchmark.objects.select_related('creditor').order_by('-sample_size', '-avg_recovery_rate')[:50]
        return render(
            request,
            'valuation/benchmarks.html',
            {
                'benchmarks': benchmarks,
                'form': form,
                'selected_category': '',
                'category_choices': Creditor.Category.choices,
                'editing_benchmark': benchmark,
                'can_manage_benchmarks': True,
                'nav_actions': _workspace_nav(request),
            },
        )


class ValuationWorkspaceView(ViewerOrManagerOrAdminReadOnlyMixin, View):
    def get(self, request):
        selected_signal = request.GET.get('signal', '')
        selected_recommendation = request.GET.get('recommendation', '')
        selected_mode = request.GET.get('mode', '')
        selected_sort = request.GET.get('sort', DEFAULT_SORT)

        portfolios = Portfolio.objects.all().prefetch_related('valuations').order_by('-purchase_date', '-id')
        portfolio_cards = []

        for portfolio in portfolios:
            portfolio_cards.append(_portfolio_card_payload(portfolio))

        if selected_signal:
            portfolio_cards = [item for item in portfolio_cards if item['signal_label'] == selected_signal]
        if selected_recommendation:
            portfolio_cards = [item for item in portfolio_cards if item['recommended_action']['label'] == selected_recommendation]
        if selected_mode:
            portfolio_cards = [item for item in portfolio_cards if item['mode_label'] == selected_mode]

        applied_sort = _sort_portfolio_cards(portfolio_cards, selected_sort)

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
            'total_face_value_display': _format_compact_money(total_face_value),
        }

        return render(
            request,
            'valuation/portfolio_list.html',
            {
                'portfolio_cards': portfolio_cards,
                'summary': summary,
                'nav_actions': _workspace_nav(request),
                'selected_signal': selected_signal,
                'selected_recommendation': selected_recommendation,
                'selected_mode': selected_mode,
                'selected_sort': applied_sort,
                'signal_options': FILTER_SIGNAL_OPTIONS,
                'recommendation_options': FILTER_RECOMMENDATION_OPTIONS,
                'mode_options': FILTER_MODE_OPTIONS,
                'sort_options': VALUATION_SORT_OPTIONS,
            },
        )


class ValuationComparisonView(ViewerOrManagerOrAdminReadOnlyMixin, View):
    def get(self, request):
        selected_ids = request.GET.getlist('portfolio')
        portfolios = Portfolio.objects.all().prefetch_related('valuations').order_by('-purchase_date', '-id')
        portfolio_cards = [_portfolio_card_payload(portfolio) for portfolio in portfolios]
        selected_cards = [
            item for item in portfolio_cards if str(item['portfolio'].id) in selected_ids
        ]
        selection_warning = None
        if len(selected_cards) > 3:
            selection_warning = 'Only the first three selected portfolios are compared at once. Narrow the selection for a cleaner side-by-side review.'
            selected_cards = selected_cards[:3]

        comparison_rows = [
            {
                'label': 'Attractiveness',
                'values': [card['attractiveness_score'] for card in selected_cards],
            },
            {
                'label': 'Expected Recovery',
                'values': [f"{card['preview']['expected_recovery_rate']}%" for card in selected_cards],
            },
            {
                'label': 'Expected Collections',
                'values': [card['preview']['expected_collections'] for card in selected_cards],
            },
            {
                'label': 'Recommended Bid',
                'values': [f"{card['preview']['recommended_bid_pct']}%" for card in selected_cards],
            },
            {
                'label': 'Projected ROI',
                'values': [f"{card['preview']['projected_roi']}%" for card in selected_cards],
            },
            {
                'label': 'Confidence',
                'values': [card['preview']['confidence_score'] for card in selected_cards],
            },
            {
                'label': 'Recommendation',
                'values': [card['recommended_action']['label'] for card in selected_cards],
            },
            {
                'label': 'Mode',
                'values': [card['mode_label'] for card in selected_cards],
            },
            {
                'label': 'Benchmark Source',
                'values': [
                    card['preview']['benchmark_context']['source'].replace('_', ' ').title() if card['preview']['benchmark_context'] else 'Rule only'
                    for card in selected_cards
                ],
            },
        ] if selected_cards else []

        lead_card = selected_cards[0] if selected_cards else None
        challenger_card = selected_cards[1] if len(selected_cards) > 1 else None
        comparison_summary = None
        if lead_card and challenger_card:
            comparison_summary = {
                'recovery_gap': _comparison_delta(lead_card['preview']['expected_recovery_rate'], challenger_card['preview']['expected_recovery_rate']),
                'bid_gap': _comparison_delta(lead_card['preview']['recommended_bid_pct'], challenger_card['preview']['recommended_bid_pct']),
                'roi_gap': _comparison_delta(lead_card['preview']['projected_roi'], challenger_card['preview']['projected_roi']),
                'confidence_gap': _comparison_delta(lead_card['preview']['confidence_score'], challenger_card['preview']['confidence_score']),
            }

        return render(
            request,
            'valuation/compare.html',
            {
                'portfolio_cards': portfolio_cards,
                'selected_cards': selected_cards,
                'selected_ids': [str(card['portfolio'].id) for card in selected_cards],
                'comparison_rows': comparison_rows,
                'comparison_summary': comparison_summary,
                'selection_warning': selection_warning,
                'nav_actions': _workspace_nav(request),
            },
        )


class ValuationImportView(ManagerOrAdminRequiredMixin, View):
    def get(self, request):
        return render(
            request,
            'valuation/import.html',
            {
                'form': ValuationImportForm(),
                'uploaded_file_name': None,
                'preview_rows': [],
                'row_errors': [],
                'summary': None,
                'nav_actions': _workspace_nav(request),
            },
        )

    def post(self, request):
        context = {
            'form': ValuationImportForm(),
            'uploaded_file_name': None,
            'preview_rows': [],
            'row_errors': [],
            'summary': None,
            'nav_actions': _workspace_nav(request),
        }
        action = request.POST.get('action', 'preview')

        if action == 'confirm':
            payload = request.session.get(VALUATION_IMPORT_SESSION_KEY)
            if not payload:
                messages.error(request, 'No valuation import preview found. Please upload and validate again.')
                return redirect('valuation-import')

            with transaction.atomic():
                creditor, _ = Creditor.objects.get_or_create(
                    name=payload['creditor_name'],
                    defaults={'category': payload['creditor_category']},
                )
                if creditor.category != payload['creditor_category']:
                    creditor.category = payload['creditor_category']
                    creditor.save(update_fields=['category'])

                portfolio_form = ValuationImportForm(payload['portfolio_data'])
                portfolio_form.fields['data_file'].required = False
                portfolio_form.fields['existing_creditor'].queryset = Creditor.objects.order_by('name')
                if not portfolio_form.is_valid():
                    messages.error(request, 'Valuation import metadata is invalid. Please upload again.')
                    return redirect('valuation-import')

                portfolio = _build_portfolio(portfolio_form, request.user)
                debtors = [Debtor(portfolio=portfolio, **row) for row in payload['cleaned_rows']]
                Debtor.objects.bulk_create(debtors, batch_size=1000)

                DataImportLog.objects.create(
                    source_file_name=payload['source_file_name'],
                    source_file_type=payload['source_file_type'],
                    status=DataImportLog.ImportStatus.SUCCESS,
                    total_rows=payload['total_rows'],
                    valid_rows=payload['valid_rows'],
                    imported_rows=payload['valid_rows'],
                    error_count=payload['error_count'],
                    details='\n'.join(payload['row_errors'][:20]),
                    portfolio=portfolio,
                    created_by=request.user if request.user.is_authenticated else None,
                )

                PortfolioUploadBatch.objects.create(
                    name=f"{portfolio.name} Acquisition Batch",
                    creditor=creditor,
                    portfolio=portfolio,
                    reporting_currency=portfolio.currency,
                    source_file_name=payload['source_file_name'],
                    uploaded_by=request.user if request.user.is_authenticated else None,
                    notes='Created from valuation import flow.',
                )

            request.session.pop(VALUATION_IMPORT_SESSION_KEY, None)
            messages.success(request, f'Valuation import completed for {portfolio.name}. The portfolio is ready for pricing analysis.')
            return redirect('valuation-preview', portfolio_id=portfolio.id)

        form = ValuationImportForm(request.POST, request.FILES)
        form.fields['existing_creditor'].queryset = Creditor.objects.order_by('name')
        context['form'] = form

        if not form.is_valid():
            return render(request, 'valuation/import.html', context)

        context['uploaded_file_name'] = form.cleaned_data['data_file'].name

        try:
            raw_rows, source_file_type = parse_uploaded_file(form.cleaned_data['data_file'])
            cleaned_rows, row_errors = validate_rows(raw_rows)
            scored_rows = _attach_risk_profile(cleaned_rows)
        except ImportValidationError as exc:
            messages.error(request, str(exc))
            DataImportLog.objects.create(
                source_file_name=form.cleaned_data['data_file'].name,
                source_file_type='unknown',
                status=DataImportLog.ImportStatus.FAILED,
                error_count=1,
                details=str(exc),
                created_by=request.user if request.user.is_authenticated else None,
            )
            return render(request, 'valuation/import.html', context)

        creditor = _resolve_creditor(form)

        DataImportLog.objects.create(
            source_file_name=form.cleaned_data['data_file'].name,
            source_file_type=source_file_type,
            status=DataImportLog.ImportStatus.PREVIEW,
            total_rows=len(raw_rows),
            valid_rows=len(scored_rows),
            error_count=len(row_errors),
            details='\n'.join(row_errors[:20]),
            created_by=request.user if request.user.is_authenticated else None,
        )

        request.session[VALUATION_IMPORT_SESSION_KEY] = {
            'source_file_name': form.cleaned_data['data_file'].name,
            'source_file_type': source_file_type,
            'portfolio_data': {
                'portfolio_name': form.cleaned_data['portfolio_name'],
                'source_company': form.cleaned_data['source_company'],
                'purchase_date': form.cleaned_data['purchase_date'].isoformat(),
                'purchase_price': str(form.cleaned_data['purchase_price']),
                'face_value': str(form.cleaned_data['face_value']),
                'currency': form.cleaned_data['currency'],
                'creditor_name': creditor.name,
                'creditor_category': creditor.category,
            },
            'creditor_name': creditor.name,
            'creditor_category': creditor.category,
            'cleaned_rows': [
                {
                    **row,
                    'outstanding_principal': str(row['outstanding_principal']),
                    'outstanding_total': str(row['outstanding_total']),
                }
                for row in scored_rows
            ],
            'row_errors': row_errors,
            'total_rows': len(raw_rows),
            'valid_rows': len(scored_rows),
            'error_count': len(row_errors),
        }

        context['preview_rows'] = scored_rows[:20]
        context['row_errors'] = row_errors[:20]
        context['summary'] = {
            'total_rows': len(raw_rows),
            'valid_rows': len(scored_rows),
            'error_count': len(row_errors),
            'creditor_name': creditor.name,
            'creditor_category': creditor.get_category_display(),
        }
        return render(request, 'valuation/import.html', context)


class ValuationReportPreviewView(ViewerOrManagerOrAdminReadOnlyMixin, View):
    def get(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio.objects.prefetch_related('valuations__factors'), id=portfolio_id)
        preview = _decorate_preview(build_rule_based_valuation(portfolio), portfolio)
        latest_valuation = portfolio.valuations.first()
        comparison_rows = [{'valuation': valuation} for valuation in portfolio.valuations.all()[:6]]
        summary = build_valuation_report_summary(
            portfolio,
            preview,
            latest_valuation=latest_valuation,
            comparison_rows=comparison_rows,
        )
        return render(
            request,
            'valuation/report_preview.html',
            {
                'portfolio': portfolio,
                'summary': summary,
                'download_excel_url': f'/valuation/portfolio/{portfolio.id}/report/excel/',
                'download_pdf_url': f'/valuation/portfolio/{portfolio.id}/report/pdf/',
                'nav_actions': _workspace_nav(request),
                'can_export_reports': getattr(request.user, 'role', None) in {'manager', 'admin'},
            },
        )


class ValuationExcelReportView(ManagerOrAdminRequiredMixin, View):
    def get(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio.objects.prefetch_related('valuations__factors'), id=portfolio_id)
        preview = build_rule_based_valuation(portfolio)
        comparison_rows = [{'valuation': valuation} for valuation in portfolio.valuations.all()[:6]]
        summary = build_valuation_report_summary(portfolio, preview, latest_valuation=portfolio.valuations.first(), comparison_rows=comparison_rows)
        content = build_valuation_excel_report(summary)

        stamp = timezone.now().strftime('%Y%m%d_%H%M')
        file_name = f'valuation_memo_{portfolio.id}_{stamp}.xlsx'
        GeneratedReport.objects.create(
            report_type=GeneratedReport.ReportType.VALUATION_MEMO,
            report_format=GeneratedReport.ReportFormat.XLSX,
            status=GeneratedReport.Status.SUCCESS,
            period_start=portfolio.purchase_date or date(2000, 1, 1),
            period_end=timezone.localdate(),
            file_name=file_name,
            file_path='downloaded-via-web',
            created_by=request.user if request.user.is_authenticated else None,
            details=f'Valuation memo export for {portfolio.name}.',
        )
        response = HttpResponse(content, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename={file_name}'
        return response


class ValuationPdfReportView(ManagerOrAdminRequiredMixin, View):
    def get(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio.objects.prefetch_related('valuations__factors'), id=portfolio_id)
        preview = build_rule_based_valuation(portfolio)
        comparison_rows = [{'valuation': valuation} for valuation in portfolio.valuations.all()[:6]]
        summary = build_valuation_report_summary(portfolio, preview, latest_valuation=portfolio.valuations.first(), comparison_rows=comparison_rows)
        content = build_valuation_pdf_report(summary)

        stamp = timezone.now().strftime('%Y%m%d_%H%M')
        file_name = f'valuation_memo_{portfolio.id}_{stamp}.pdf'
        GeneratedReport.objects.create(
            report_type=GeneratedReport.ReportType.VALUATION_MEMO,
            report_format=GeneratedReport.ReportFormat.PDF,
            status=GeneratedReport.Status.SUCCESS,
            period_start=portfolio.purchase_date or date(2000, 1, 1),
            period_end=timezone.localdate(),
            file_name=file_name,
            file_path='downloaded-via-web',
            created_by=request.user if request.user.is_authenticated else None,
            details=f'Valuation memo export for {portfolio.name}.',
        )
        response = HttpResponse(content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename={file_name}'
        return response


class PortfolioValuationPreviewView(ViewerOrManagerOrAdminReadOnlyMixin, View):
    def get(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio.objects.prefetch_related('valuations__factors'), id=portfolio_id)
        latest_valuation = portfolio.valuations.first()

        valuation_history = list(portfolio.valuations.all()[:6])
        comparison_rows = []
        comparison_summary = None
        if valuation_history:
            newest = valuation_history[0]
            oldest = valuation_history[-1]
            comparison_summary = {
                'run_count': len(valuation_history),
                'latest_method': newest.get_valuation_method_display(),
                'recovery_delta': newest.expected_recovery_rate - oldest.expected_recovery_rate,
                'bid_delta': newest.recommended_bid_pct - oldest.recommended_bid_pct,
                'roi_delta': newest.projected_roi - oldest.projected_roi,
            }

            previous = None
            for valuation in valuation_history:
                comparison_rows.append({
                    'valuation': valuation,
                    'delta_recovery': valuation.expected_recovery_rate - previous.expected_recovery_rate if previous else None,
                    'delta_bid': valuation.recommended_bid_pct - previous.recommended_bid_pct if previous else None,
                    'delta_roi': valuation.projected_roi - previous.projected_roi if previous else None,
                })
                previous = valuation

        preview = _decorate_preview(build_rule_based_valuation(portfolio), portfolio)
        latest_saved = None
        if latest_valuation:
            latest_saved = {
                'expected_collections_display': _format_compact_money(latest_valuation.expected_collections),
                'recommended_bid_amount_display': _format_compact_money(latest_valuation.recommended_bid_amount),
            }

        return render(
            request,
            'valuation/preview.html',
            {
                'portfolio': portfolio,
                'preview': preview,
                'recommended_action': _recommended_action(preview, _attractiveness_score(preview)),
                'latest_valuation': latest_valuation,
                'latest_saved': latest_saved,
                'latest_factors': latest_valuation.factors.all()[:8] if latest_valuation else [],
                'valuation_history': valuation_history,
                'comparison_rows': comparison_rows,
                'comparison_summary': comparison_summary,
                'nav_actions': _workspace_nav(request),
                'can_run_valuation': getattr(request.user, 'role', None) in {'manager', 'admin'},
                'can_export_reports': getattr(request.user, 'role', None) in {'manager', 'admin'},
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
