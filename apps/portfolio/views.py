from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render

from apps.portfolio.forms import PortfolioImportForm
from apps.portfolio.importers import ImportValidationError, parse_uploaded_file, validate_rows
from apps.portfolio.models import DataImportLog, Debtor, Portfolio
from apps.scoring.services import calculate_risk_profile
from apps.users.decorators import manager_or_admin_required


IMPORT_SESSION_KEY = 'portfolio_import_payload'


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


@login_required
@manager_or_admin_required
def portfolio_import_view(request):
    context = {
        'form': PortfolioImportForm(),
        'uploaded_file_name': None,
        'preview_rows': [],
        'row_errors': [],
        'summary': None,
    }

    if request.method == 'POST':
        action = request.POST.get('action', 'preview')

        if action == 'confirm':
            payload = request.session.get(IMPORT_SESSION_KEY)
            if not payload:
                messages.error(request, 'No preview data found. Please upload and validate again.')
                return redirect('portfolio-import')

            with transaction.atomic():
                portfolio_form = PortfolioImportForm(payload['portfolio_data'])
                if not portfolio_form.is_valid():
                    messages.error(request, 'Portfolio metadata is invalid. Please upload again.')
                    return redirect('portfolio-import')

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

            request.session.pop(IMPORT_SESSION_KEY, None)
            messages.success(request, f'Imported {payload["valid_rows"]} debtors successfully.')
            return redirect('portfolio-import')

        form = PortfolioImportForm(request.POST, request.FILES)
        context['form'] = form

        if not form.is_valid():
            return render(request, 'portfolio/import_data.html', context)

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
            return render(request, 'portfolio/import_data.html', context)

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

        request.session[IMPORT_SESSION_KEY] = {
            'source_file_name': form.cleaned_data['data_file'].name,
            'source_file_type': source_file_type,
            'portfolio_data': {
                'portfolio_name': form.cleaned_data['portfolio_name'],
                'source_company': form.cleaned_data['source_company'],
                'purchase_date': form.cleaned_data['purchase_date'].isoformat(),
                'purchase_price': str(form.cleaned_data['purchase_price']),
                'face_value': str(form.cleaned_data['face_value']),
                'currency': form.cleaned_data['currency'],
            },
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
        }

    return render(request, 'portfolio/import_data.html', context)
