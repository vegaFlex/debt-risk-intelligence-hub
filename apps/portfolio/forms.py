from django import forms


class PortfolioImportForm(forms.Form):
    portfolio_name = forms.CharField(max_length=255)
    source_company = forms.CharField(max_length=255, required=False)
    purchase_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    purchase_price = forms.DecimalField(max_digits=14, decimal_places=2)
    face_value = forms.DecimalField(max_digits=14, decimal_places=2)
    currency = forms.CharField(max_length=3, initial='EUR')
    data_file = forms.FileField(help_text='Upload CSV or XLSX file with debtor records.')
