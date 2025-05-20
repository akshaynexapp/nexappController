from django.urls import path, include
from rest_framework.routers import DefaultRouter

from sdwan_tunnel.api.views import (
    TunnelViewSet,
    VpnTopologyDeployView,
    DevicePeerViewSet,
    ConfigHistoryViewSet,
    TunnelStatusViewSet,
    AuditLogEntryViewSet
)

router = DefaultRouter()
router.register('tunnels', TunnelViewSet, basename='tunnel')
router.register('peers', DevicePeerViewSet, basename='devicepeer')
router.register('history', ConfigHistoryViewSet, basename='confighistory')
router.register('status', TunnelStatusViewSet, basename='tunnelstatus')
router.register('audit', AuditLogEntryViewSet, basename='auditlog')
 
urlpatterns = [
    path('', include(router.urls)),
    path('deploy/', VpnTopologyDeployView.as_view(), name='vpn-deploy'),

]


