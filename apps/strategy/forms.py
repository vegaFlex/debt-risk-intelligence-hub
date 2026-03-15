from django import forms

from apps.strategy.models import ActionRule


class ActionRuleForm(forms.ModelForm):
    class Meta:
        model = ActionRule
        fields = [
            'name',
            'risk_band',
            'debtor_status',
            'dpd_min',
            'dpd_max',
            'requires_phone',
            'requires_email',
            'recommended_action',
            'recommended_channel',
            'base_uplift_pct',
            'priority_weight',
            'active',
            'notes',
        ]

    def clean(self):
        cleaned_data = super().clean()
        dpd_min = cleaned_data.get('dpd_min')
        dpd_max = cleaned_data.get('dpd_max')
        if dpd_min is not None and dpd_max is not None and dpd_min > dpd_max:
            self.add_error('dpd_max', 'DPD max must be greater than or equal to DPD min.')
        return cleaned_data
