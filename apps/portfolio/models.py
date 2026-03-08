from django.conf import settings
from django.db import models


class Portfolio(models.Model):
    name = models.CharField(max_length=255)
    source_company = models.CharField(max_length=255, blank=True)
    purchase_date = models.DateField()
    purchase_price = models.DecimalField(max_digits=14, decimal_places=2)
    face_value = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default='BGN')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='portfolios',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-purchase_date', '-id')

    def __str__(self):
        return self.name


class Debtor(models.Model):
    class RiskBand(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'

    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='debtors')
    external_id = models.CharField(max_length=64)
    full_name = models.CharField(max_length=255)
    national_id = models.CharField(max_length=32, blank=True)
    phone_number = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    region = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=40, default='new')
    days_past_due = models.PositiveIntegerField(default=0)
    outstanding_principal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    outstanding_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    risk_band = models.CharField(max_length=10, choices=RiskBand.choices, default=RiskBand.MEDIUM)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-outstanding_total', '-id')
        unique_together = ('portfolio', 'external_id')

    def __str__(self):
        return f'{self.full_name} ({self.external_id})'


class Payment(models.Model):
    debtor = models.ForeignKey(Debtor, on_delete=models.CASCADE, related_name='payments')
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment_date = models.DateField()
    channel = models.CharField(max_length=50, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    is_confirmed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-payment_date', '-id')

    def __str__(self):
        return f'{self.debtor.full_name} - {self.paid_amount}'


class CallLog(models.Model):
    class Outcome(models.TextChoices):
        NO_ANSWER = 'no_answer', 'No Answer'
        REFUSED = 'refused', 'Refused'
        PROMISE_TO_PAY = 'promise_to_pay', 'Promise To Pay'
        PAID = 'paid', 'Paid'
        WRONG_CONTACT = 'wrong_contact', 'Wrong Contact'

    debtor = models.ForeignKey(Debtor, on_delete=models.CASCADE, related_name='call_logs')
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='call_logs',
    )
    call_datetime = models.DateTimeField()
    outcome = models.CharField(max_length=20, choices=Outcome.choices)
    duration_seconds = models.PositiveIntegerField(default=0)
    promised_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-call_datetime', '-id')

    def __str__(self):
        return f'{self.debtor.full_name} - {self.outcome}'


class PromiseToPay(models.Model):
    class PromiseStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        KEPT = 'kept', 'Kept'
        BROKEN = 'broken', 'Broken'
        CANCELED = 'canceled', 'Canceled'

    debtor = models.ForeignKey(Debtor, on_delete=models.CASCADE, related_name='promises_to_pay')
    call_log = models.OneToOneField(
        CallLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promise_to_pay',
    )
    promised_amount = models.DecimalField(max_digits=14, decimal_places=2)
    due_date = models.DateField()
    status = models.CharField(max_length=10, choices=PromiseStatus.choices, default=PromiseStatus.PENDING)
    fulfilled_payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fulfilled_promises',
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-due_date', '-id')

    def __str__(self):
        return f'{self.debtor.full_name} - {self.promised_amount}'
