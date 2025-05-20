"""
DRF API Views for SD-WAN Tunnel app, including deployment endpoint.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from django.shortcuts import render
 
from sdwan_tunnel.models import (
    Tunnel,
    DevicePeer,
    ConfigHistory,
    TunnelStatus,
    AuditLogEntry
)
from sdwan_tunnel.api.serializers import (
    TunnelSerializer,
    DevicePeerSerializer,
    ConfigHistorySerializer,
    TunnelStatusSerializer,
    AuditLogEntrySerializer
)
from sdwan_tunnel.services.deployment_manager import deploy_vpn_topology


class TunnelViewSet(viewsets.ModelViewSet):
    """CRUD operations for Tunnel with push and rollback endpoints."""
    queryset = Tunnel.objects.all()
    serializer_class = TunnelSerializer
    permission_classes = [IsAuthenticated]
 
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'organizationuser'):
            org = user.organizationuser.organization
            return Tunnel.objects.filter(organization=org)
        return Tunnel.objects.none()
 
    @action(detail=True, methods=['post'], url_path='push')
    def push(self, request, pk=None):
        tunnel = self.get_object()
        result = tunnel.push_to_agent()
        return Response(result, status=status.HTTP_200_OK)
 
    @action(detail=True, methods=['post'], url_path='rollback')
    def rollback(self, request, pk=None):
        tunnel = self.get_object()
        result = tunnel.rollback_last_config()
        return Response(result, status=status.HTTP_200_OK)
    
    
 
class VpnTopologyDeployView(APIView):
    """Endpoint to trigger VPN topology deployment via JSON payload."""
    permission_classes = [IsAuthenticated]
 
    def post(self, request):
        # Expect JSON payload: {'tunnel_id': <int>, 'full_replace': <bool>}
        data = request.data
        user = request.user
        result = deploy_vpn_topology(data, user)
        return Response(result, status=status.HTTP_200_OK)
 
 
class DevicePeerViewSet(viewsets.ModelViewSet):
    queryset = DevicePeer.objects.all()
    serializer_class = DevicePeerSerializer
    permission_classes = [IsAuthenticated]
 
 
class ConfigHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ConfigHistory.objects.all()
    serializer_class = ConfigHistorySerializer
    permission_classes = [IsAuthenticated]
 
 
class TunnelStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TunnelStatus.objects.all()
    serializer_class = TunnelStatusSerializer
    permission_classes = [IsAuthenticated]
 
 
class AuditLogEntryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLogEntry.objects.all()
    serializer_class = AuditLogEntrySerializer
    permission_classes = [IsAuthenticated]
 
 
def tunnelconfig_form(request):
    return render(request, 'sdwan_tunnel/tunnelconfig_form.html')