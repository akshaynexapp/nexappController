from django.urls import path, include
from rest_framework.routers import DefaultRouter

from sdwan_tunnel.api.views import (
    TunnelViewSet,
    VpnTopologyDeployView,
    ConfigHistoryViewSet,
    AuditLogEntryViewSet,
    HubViewSet,
    SpokeViewSet , JobViewSet ,PathLabelViewSet ,
    LinkMonitoringViewSet, QOSPolicyViewSet ,
     FullMeshViewSet
)

router = DefaultRouter()
router.register('tunnels', TunnelViewSet, basename='tunnel')
router.register('history', ConfigHistoryViewSet, basename='confighistory')
router.register('audit', AuditLogEntryViewSet, basename='auditlog')
router.register('hub', HubViewSet, basename='hub')
router.register('spoke', SpokeViewSet, basename='spoke')
router.register('job', JobViewSet, basename='job')
router.register('pathlabel', PathLabelViewSet, basename='pathlabel')
router.register('linkmonitoring', LinkMonitoringViewSet, basename='linkmonitoring')
router.register('qos', QOSPolicyViewSet, basename='qos')
router.register('fullmesh', FullMeshViewSet, basename='fullmesh')



urlpatterns = [
    path('', include(router.urls)),
    path('deploy/', VpnTopologyDeployView.as_view(), name='vpn-deploy'),

]


