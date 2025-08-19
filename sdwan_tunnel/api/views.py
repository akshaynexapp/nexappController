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
    ConfigHistory,
    AuditLogEntry,
    Hub,
    Spoke ,Job
)
from sdwan_tunnel.api.serializers import (
    TunnelSerializer,
    ConfigHistorySerializer,
    AuditLogEntrySerializer,
    HubSerializer,
    SpokeSerializer , JobSerializer,PathLabelSerializer ,
    LinkMonitoringSerializer , QOSPolicySerializer 
    
)
from sdwan_tunnel.services.deployment_manager import deploy_vpn_topology
from rest_framework.permissions import IsAuthenticated, AllowAny
from sdwan_tunnel.models.sdwanzone import SDWANZone
from sdwan_tunnel.models.pathlabel import PathLabel
from sdwan_tunnel.models.linkmonitoring import LinkMonitoring
from sdwan_tunnel.models.qos import QOSPolicy
from rest_framework import decorators, response
from django.utils import timezone
from sdwan_tunnel.models.fullmesh import FullMesh
from .serializers import FullMeshSerializer

class TunnelViewSet(viewsets.ModelViewSet):
    """No-auth CRUD for Tunnel with push/rollback endpoints."""
    queryset = Tunnel.objects.all()
    serializer_class = TunnelSerializer
    permission_classes = [AllowAny]   # <-- allow everyone

    def get_queryset(self):
        # No filtering by organization or user
        return Tunnel.objects.all()

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
 
 
class JobViewSet(viewsets.ModelViewSet):
    """No-auth CRUD for Tunnel with push/rollback endpoints."""
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    permission_classes = [AllowAny]   # <-- allow everyone


class PathLabelViewSet(viewsets.ModelViewSet):
    """No-auth CRUD for Tunnel with push/rollback endpoints."""
    queryset = PathLabel.objects.all()
    serializer_class = PathLabelSerializer
    permission_classes = [AllowAny]   # <-- allow everyone


class ConfigHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ConfigHistory.objects.all()
    serializer_class = ConfigHistorySerializer
    permission_classes = [IsAuthenticated]
  
class AuditLogEntryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLogEntry.objects.all()
    serializer_class = AuditLogEntrySerializer
    permission_classes = [IsAuthenticated]

class HubViewSet(viewsets.ModelViewSet):
    queryset = Hub.objects.all()
    serializer_class = HubSerializer
    permission_classes = [AllowAny]

class SpokeViewSet(viewsets.ModelViewSet):
    queryset = Spoke.objects.all()
    serializer_class = SpokeSerializer
    permission_classes = [AllowAny]

class LinkMonitoringViewSet(viewsets.ModelViewSet):
    queryset = LinkMonitoring.objects.all()
    serializer_class = LinkMonitoringSerializer
    permission_classes = [AllowAny]

class QOSPolicyViewSet(viewsets.ModelViewSet):
    queryset = QOSPolicy.objects.all()
    serializer_class = QOSPolicySerializer
    permission_classes = [AllowAny]
 

  # <-- allow everyone

class FullMeshViewSet(viewsets.ModelViewSet):
    queryset = FullMesh.objects.all().order_by('-updated_at')
    serializer_class = FullMeshSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = self.request.user
        mesh = serializer.save(
            created_by=user,
            organization=getattr(user, 'organization', None) or getattr(user, 'organizations', None) and user.organizations.first()
        )
        # optional timestamp
        mesh.last_synced_at = timezone.now()
        mesh.save(update_fields=['last_synced_at'])

    # @decorators.action(detail=True, methods=['get'])
    # def pairs(self, request, pk=None):
    #     mesh = self.get_object()
    #     data = mesh.pair_table()
    #     ser = PairRowSerializer(data, many=True)
    #     return response.Response(ser.data)




def tunnelconfig_form(request):
    return render(request, 'sdwan_tunnel/tunnelconfig_form.html')