
"""
DRF API Views for SD-WAN Tunnel app, including deployment endpoint.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import render
from ..models.firewall import Firewall
from ..models.application import Application, Category
from traffic_application.api.serializers import FirewallSerializer , ApplicationSerializer, CategorySerializer
from rest_framework.permissions import AllowAny




class FirewallViewSet(viewsets.ModelViewSet):
    """No-auth CRUD for Tunnel with push/rollback endpoints."""
    queryset = Firewall.objects.all()
    serializer_class = FirewallSerializer
    permission_classes = [AllowAny] 


class ApplicationViewSet(viewsets.ModelViewSet):
    """No-auth CRUD for Tunnel with push/rollback endpoints."""
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    permission_classes = [AllowAny] 

class CategoryViewSet(viewsets.ModelViewSet):
    """No-auth CRUD for Tunnel with push/rollback endpoints."""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny] 