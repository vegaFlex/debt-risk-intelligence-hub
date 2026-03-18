from django import forms

from apps.valuation.models import Creditor


class ValuationImportForm(forms.Form):
    portfolio_name = forms.CharField(max_length=255)
    source_company = forms.CharField(max_length=255, required=False)
    purchase_date = forms.DateField(
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'type': 'text',
                'placeholder': 'YYYY-MM-DD',
                'inputmode': 'numeric',
                'autocomplete': 'off',
                'spellcheck': 'false',
                'class': 'date-icon-field',
            },
        ),
    )
    purchase_price = forms.DecimalField(max_digits=14, decimal_places=2)
    face_value = forms.DecimalField(max_digits=14, decimal_places=2)
    currency = forms.CharField(max_length=3, initial='EUR')
    existing_creditor = forms.ModelChoiceField(
        queryset=Creditor.objects.order_by('name'),
        required=False,
        empty_label='Select existing creditor',
    )
    creditor_name = forms.CharField(max_length=255, required=False)
    creditor_category = forms.ChoiceField(choices=Creditor.Category.choices, required=False)
    data_file = forms.FileField(help_text='Upload CSV file with debtor records for valuation.')

    def clean(self):
        cleaned_data = super().clean()
        existing_creditor = cleaned_data.get('existing_creditor')
        creditor_name = (cleaned_data.get('creditor_name') or '').strip()
        creditor_category = cleaned_data.get('creditor_category')

        if not existing_creditor and not creditor_name:
            self.add_error('existing_creditor', 'Select an existing creditor or enter a new creditor name.')

        if creditor_name and not creditor_category:
            self.add_error('creditor_category', 'Choose a creditor category when entering a new creditor.')

        return cleaned_data


from apps.valuation.models import HistoricalBenchmark


class HistoricalBenchmarkForm(forms.ModelForm):
    class Meta:
        model = HistoricalBenchmark
        fields = [
            'creditor',
            'creditor_category',
            'product_type',
            'dpd_band',
            'balance_band',
            'region',
            'avg_recovery_rate',
            'avg_contact_rate',
            'avg_ptp_rate',
            'avg_conversion_rate',
            'sample_size',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['creditor'].queryset = Creditor.objects.order_by('name')
        self.fields['product_type'].required = False
        self.fields['region'].required = False

