from django.contrib import messages
from django.shortcuts import render

from apps.portfolio.forms import PortfolioImportForm
from apps.portfolio.importers import ImportValidationError, parse_uploaded_file, validate_rows


def portfolio_import_view(request):
    context = {
        'form': PortfolioImportForm(),
        'uploaded_file_name': None,
        'preview_rows': [],
        'row_errors': [],
        'summary': None,
    }

    if request.method == 'POST':
        form = PortfolioImportForm(request.POST, request.FILES)
        context['form'] = form

        if not form.is_valid():
            return render(request, 'portfolio/import_data.html', context)

        context['uploaded_file_name'] = form.cleaned_data['data_file'].name

        try:
            raw_rows, _ = parse_uploaded_file(form.cleaned_data['data_file'])
            cleaned_rows, row_errors = validate_rows(raw_rows)
        except ImportValidationError as exc:
            messages.error(request, str(exc))
            return render(request, 'portfolio/import_data.html', context)

        context['preview_rows'] = cleaned_rows[:20]
        context['row_errors'] = row_errors[:20]
        context['summary'] = {
            'total_rows': len(raw_rows),
            'valid_rows': len(cleaned_rows),
            'error_count': len(row_errors),
        }

    return render(request, 'portfolio/import_data.html', context)
