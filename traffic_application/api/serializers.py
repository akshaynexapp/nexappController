"""
DRF serializers for SD-WAN Tunnel app models.
Covers CRUD and nested representations.
"""
from rest_framework import serializers
from openwisp_users.models import OrganizationUser, Organization
from openwisp_controller.config.models import Config as Device

from ..models.firewall import Firewall
from ..models.application import Application, Category



class FirewallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Firewall
        fields = ['id', 'name', 'created_at']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "tag_id", "name", "label", "description"]
        read_only_fields = ["id"]


class ApplicationSerializer(serializers.ModelSerializer):
    # pick categories by their Netify tag_id
    category = serializers.SlugRelatedField(
        slug_field="tag_id",
        queryset=Category.objects.all(),
    )

    domains = serializers.ListField(
        child=serializers.CharField(max_length=253),
        allow_empty=True,
        required=False,
    )
    meta = serializers.JSONField(required=False)

    class Meta:
        model = Application
        fields = [
            "id", "application_name",
            "category", "domains", "meta", "last_update",
        ]
        read_only_fields = ["id"]