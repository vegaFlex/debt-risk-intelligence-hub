from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path

from config import docs_views

admin.site.site_header = 'Debt & Risk Admin'
admin.site.site_title = 'Debt & Risk Admin'
admin.site.index_title = 'Administration workspace'


def root_redirect(_request):
    return redirect('dashboard-home')


urlpatterns = [
    path('docs/user-guide/', docs_views.user_guide, name='docs-user-guide'),
    path('docs/buyer-guide/', docs_views.buyer_guide, name='docs-buyer-guide'),
    path('docs/buyer-one-pager/', docs_views.buyer_one_pager, name='docs-buyer-one-pager'),
    path('', root_redirect, name='root-redirect'),
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('portfolio/', include('apps.portfolio.urls')),
    path('api/', include('apps.portfolio.api_urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('reports/', include('apps.reports.urls')),
    path('valuation/', include('apps.valuation.urls')),
]

