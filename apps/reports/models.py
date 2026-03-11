from django.conf import settings
from django.db import models


class GeneratedReport(models.Model):
    class ReportFormat(models.TextChoices):
        XLSX = 'xlsx', 'XLSX'
        PDF = 'pdf', 'PDF'

    class ReportType(models.TextChoices):
        MANAGEMENT_WEEKLY = 'management_weekly', 'Management Weekly'
        VALUATION_MEMO = 'valuation_memo', 'Valuation Memo'

    class Status(models.TextChoices):
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'

    report_type = models.CharField(max_length=40, choices=ReportType.choices)
    report_format = models.CharField(max_length=10, choices=ReportFormat.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SUCCESS)
    period_start = models.DateField()
    period_end = models.DateField()
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500, blank=True)
    details = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='generated_reports',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at', '-id')

    def __str__(self):
        return f'{self.report_type} ({self.report_format}) {self.period_start} - {self.period_end}'
