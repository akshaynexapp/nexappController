from django.urls import path

from . import views
from .views import device_sla_proxy

app_name = 'monitoring_general'

urlpatterns = [
    path(
        'api/v1/monitoring/dashboard/',
        views.dashboard_timeseries,
        name='api_dashboard_timeseries',
    ),
     path('api/device-sla-proxy/', device_sla_proxy, name='device_sla_proxy'),
]
