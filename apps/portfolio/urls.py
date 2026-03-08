from django.urls import path

from apps.portfolio.views import portfolio_import_view


urlpatterns = [
    path('import/', portfolio_import_view, name='portfolio-import'),
]
