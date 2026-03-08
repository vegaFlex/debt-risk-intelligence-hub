from django.contrib import admin

from apps.portfolio.models import CallLog, Debtor, Payment, Portfolio, PromiseToPay


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ('name', 'source_company', 'purchase_date', 'purchase_price', 'face_value', 'created_at')
    search_fields = ('name', 'source_company')
    list_filter = ('purchase_date', 'currency')


@admin.register(Debtor)
class DebtorAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'portfolio', 'status', 'days_past_due', 'outstanding_total', 'risk_band')
    search_fields = ('full_name', 'external_id', 'national_id', 'phone_number', 'email')
    list_filter = ('status', 'risk_band', 'region')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('debtor', 'paid_amount', 'payment_date', 'channel', 'is_confirmed')
    search_fields = ('debtor__full_name', 'reference')
    list_filter = ('payment_date', 'channel', 'is_confirmed')


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display = ('debtor', 'agent', 'call_datetime', 'outcome', 'duration_seconds')
    search_fields = ('debtor__full_name', 'agent__username')
    list_filter = ('outcome', 'call_datetime')


@admin.register(PromiseToPay)
class PromiseToPayAdmin(admin.ModelAdmin):
    list_display = ('debtor', 'promised_amount', 'due_date', 'status', 'fulfilled_payment')
    search_fields = ('debtor__full_name',)
    list_filter = ('status', 'due_date')
