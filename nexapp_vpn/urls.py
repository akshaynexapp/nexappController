
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TunnelViewSet,
    TunnelStatusLogViewSet,
    TunnelConfigHistoryViewSet,
    TunnelHealthMetricViewSet,
    DevicePeerViewSet
)
# from . import views

 
router = DefaultRouter()
router.register(r'tunnels', TunnelViewSet, basename='tunnel')
router.register(r'status-logs', TunnelStatusLogViewSet, basename='statuslog')
router.register(r'config-history', TunnelConfigHistoryViewSet, basename='confighistory')
router.register(r'health-metrics', TunnelHealthMetricViewSet, basename='healthmetric')
router.register(r'device-peers', DevicePeerViewSet, basename='devicepeer')
 
urlpatterns = [
    path('/', include(router.urls)),
    # path('', views.tunnelconfig_form, name='tunnelconfig_form'), 
]