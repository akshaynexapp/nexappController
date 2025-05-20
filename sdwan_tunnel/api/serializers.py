"""
DRF serializers for SD-WAN Tunnel app models.
Covers CRUD and nested representations.
"""
from rest_framework import serializers
from openwisp_users.models import OrganizationUser, Organization
from openwisp_controller.config.models import Config as Device
from sdwan_tunnel.models import (
    Tunnel,
    DevicePeer,
    ConfigHistory,
    TunnelStatus,
    AuditLogEntry
)
from sdwan_tunnel.protocols.ipsec.client import fetch_online_devices_by_names

 
class DevicePeerSerializer(serializers.ModelSerializer):
    class Meta:
        model = DevicePeer
        fields = [
            'id', 'tunnel', 'local_device', 'peer_device',
            'local_ip', 'peer_ip', 'link_subnet', 'local_role', 'peer_role', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
 
class ConfigHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfigHistory
        fields = [
            'id', 'tunnel', 'user', 'action', 'payload_hash', 'payload',
            'config_text', 'timestamp','generated_at', 'triggered_by'
        ]
        read_only_fields = ['id', 'timestamp']
 
class TunnelStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TunnelStatus
        fields = [
            'id', 'tunnel', 'is_up', 'latency_ms', 'jitter_ms',
            'packet_loss_percent', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']
 
class AuditLogEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLogEntry
        fields = [
            'id', 'user', 'event', 'topology_id', 'devices', 'details', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']
 
class TunnelSerializer(serializers.ModelSerializer):
    device_peers = DevicePeerSerializer(many=True, read_only=True)
    config_histories = ConfigHistorySerializer(many=True, read_only=True)
    statuses = TunnelStatusSerializer(many=True, read_only=True)
    audit_logs = AuditLogEntrySerializer(many=True, read_only=True)
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all())
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=OrganizationUser.objects.all(), required=False, allow_null=True
    )
    device_a = serializers.PrimaryKeyRelatedField(queryset=Device.objects.none())
    device_b = serializers.PrimaryKeyRelatedField(many=True, queryset=Device.objects.none())
 
    class Meta:
        model = Tunnel
        fields = [
            'id', 'organization', 'name', 'vpn_type', 'mode', 'template',
            'status', 'is_enabled', 'notes', 'created_by',
            'last_pushed_at', 'last_config_hash', 'created_at', 'updated_at',
            'device_a', 'device_b', 'device_peers',
            'ike_version', 'ike_encryption_algorithm', 'ike_integrity_algorithm',
            'ike_dh_group', 'ike_lifetime',
            'esp_encryption_algorithm', 'esp_integrity_algorithm', 'esp_dh_group',
            'esp_lifetime', 'local_identifier', 'remote_identifier',
            'config_histories', 'statuses', 'audit_logs' 
        ]
        read_only_fields = [
            'id', 'status', 'last_pushed_at', 'last_config_hash',
            'created_at', 'updated_at'
        ]
    
    def validate(self, data):
        # Ensure mode and device assignments
        mode = data.get('mode', self.instance.mode if self.instance else None)
        if mode == 'site_to_site' and not data.get('device_a'):
            raise serializers.ValidationError("Device A (hub) must be set for site-to-site mode.")
        return data