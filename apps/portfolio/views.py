from django.shortcuts import render

from apps.portfolio.forms import PortfolioImportForm


def portfolio_import_view(request):
    form = PortfolioImportForm(request.POST or None, request.FILES or None)
    uploaded_file_name = None

    if request.method == 'POST' and form.is_valid():
        uploaded_file_name = form.cleaned_data['data_file'].name

    return render(
        request,
        'portfolio/import_data.html',
        {
            'form': form,
            'uploaded_file_name': uploaded_file_name,
            'preview_rows': [],
            'row_errors': [],
            'summary': None,
        },
    )
