 
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Tunnel, TunnelStatusLog, TunnelConfigHistory, TunnelHealthMetric, DevicePeer
from .serializers import (
    TunnelSerializer,
    TunnelStatusLogSerializer,
    TunnelConfigHistorySerializer,
    TunnelHealthMetricSerializer,
    DevicePeerSerializer
)
from django.shortcuts import render

class TunnelViewSet(viewsets.ModelViewSet):
    queryset = Tunnel.objects.all()
    serializer_class = TunnelSerializer
 
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'organizationuser'):
            return Tunnel.objects.filter(organization=user.organizationuser.organization)
        return Tunnel.objects.none()
 
    @action(detail=True, methods=['post'])
    def push(self, request, pk=None):
        tunnel = self.get_object()
        result = tunnel.push_to_agent()
        return Response(result)
 
    @action(detail=True, methods=['post'])
    def rollback(self, request, pk=None):
        tunnel = self.get_object()
        result = tunnel.rollback_last_config()
        return Response(result)
 
 
class TunnelStatusLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TunnelStatusLog.objects.all()
    serializer_class = TunnelStatusLogSerializer
 
 
class TunnelConfigHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TunnelConfigHistory.objects.all()
    serializer_class = TunnelConfigHistorySerializer
 
 
class TunnelHealthMetricViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TunnelHealthMetric.objects.all()
    serializer_class = TunnelHealthMetricSerializer
 
 
class DevicePeerViewSet(viewsets.ModelViewSet):
    queryset = DevicePeer.objects.all()
    serializer_class = DevicePeerSerializer

def tunnelconfig_form(request):
    return render(request, 'nexappvpn/tunnelconfig_form.html')
