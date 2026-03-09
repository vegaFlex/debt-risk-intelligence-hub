from django.contrib import admin

from apps.reports.models import GeneratedReport


@admin.register(GeneratedReport)
class GeneratedReportAdmin(admin.ModelAdmin):
    list_display = (
        'report_type',
        'report_format',
        'status',
        'period_start',
        'period_end',
        'file_name',
        'created_at',
    )
    list_filter = ('report_type', 'report_format', 'status', 'period_start', 'period_end')
    search_fields = ('file_name', 'file_path')
