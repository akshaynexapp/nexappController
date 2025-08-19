"""
DRF serializers for SD-WAN Tunnel app models.
Covers CRUD and nested representations.
"""
from rest_framework import serializers
from openwisp_users.models import OrganizationUser, Organization
from openwisp_controller.config.models import Config as Device
from sdwan_tunnel.models import (
    Tunnel,
    ConfigHistory,
    AuditLogEntry,
    Hub, Spoke , Job
)
from sdwan_tunnel.models.pathlabel import PathLabel
from sdwan_tunnel.models.sdwanzone import SDWANZone
from sdwan_tunnel.models.qos import QOSPolicy
from sdwan_tunnel.models.linkmonitoring import LinkMonitoring

from sdwan_tunnel.protocols.ipsec.client import fetch_online_devices_by_names
from sdwan_tunnel.models.fullmesh import FullMesh


class PathLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = PathLabel
        fields = ['id', 'name', 'description', 'direct_internet_access','color', 'created_at']


class ConfigHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfigHistory
        fields = [
            'id', 'tunnel',  'action',  'payload',
             
        ]
        read_only_fields = ['id', 'config_hash','created_at']

class AuditLogEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLogEntry
        fields = [
            'id', 'user', 'event', 'topology_id', 'devices', 'details', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']



class JobSerializer(serializers.ModelSerializer):
    spoke_name = serializers.CharField(source='spoke.device.name', read_only=True)
    triggered_by_username = serializers.CharField(source='triggered_by.username', read_only=True)

    class Meta:
        model = Job
        fields = [
            'id',
            'spoke',  # FK ID
            'spoke_name',  # Human-readable name
            'triggered_by',  # FK ID
            'triggered_by_username',  # Human-readable username
            'status',
            'message',
            'created_at',
            'finished_at'
        ]
        read_only_fields = ['status', 'message', 'created_at', 'finished_at']



class HubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hub
        fields = [
            'id', 'local_device', 'organization', 'name',  'created_by',
            'is_enabled', 'local_ip', 'wan_ip', 'subnet', 'forceencaps', 'dpdaction','ipcomp',
            'ike_version', 'ike_encryption_algorithm', 'ike_integrity_algorithm',
            'ike_diffie_hellman_group', 'ike_key_lifetime',
            'esp_encryption_algorithm', 'esp_integrity_algorithm', 'esp_diffie_hellman_group',
            'esp_key_lifetime','last_pushed_at','uuid','local_ip',
            'last_config_hash', 'pre_shared_key', 'created_at', 'updated_at', 'last_config_payload',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        
class SpokeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Spoke
        fields = [
            'id', 'device', 'hub_device', 'status', 'created_by',
            'is_enabled', 'local_ip', 'wan_ip', 'subnet',
            'last_pushed_at','latency', 'jitter', 'packet_loss','uuid','local_ip',
             'created_at', 'updated_at', 
        ]
        read_only_fields = ['id', 'created_at','last_push_message', 'updated_at', 'latency', 'jitter', 'packet_loss']
        

class TunnelSerializer(serializers.ModelSerializer):

    config_histories = ConfigHistorySerializer(many=True, read_only=True)
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
            'id', 'organization', 'name', 'vpn_type', 'mode', 
            'status', 'is_enabled', 'notes', 'created_by',
            'last_pushed_at', 'last_config_hash', 'created_at', 'updated_at',
            'device_a', 'device_b',  
            'ike_version', 'ike_encryption_algorithm', 'ike_integrity_algorithm',
            'ike_diffie_hellman_group', 'ike_key_lifetime',
            'esp_encryption_algorithm', 'esp_integrity_algorithm', 'esp_diffie_hellman_group',
            'esp_key_lifetime','uuid_a', 'uuid_b', 'local_ip_b','local_ip_a',
            'config_histories',  'audit_logs' 
        ]
        read_only_fields = [
            'id', 'status','last_push_message', 'last_pushed_at', 'last_config_hash',
            'created_at', 'updated_at','latency', 'jitter' ,'packet_loss'
        ]
    
    def validate(self, data):
        # Ensure mode and device assignments
        mode = data.get('mode', self.instance.mode if self.instance else None)
        if mode == 'site_to_site' and not data.get('device_a'):
            raise serializers.ValidationError("Device A (hub) must be set for site-to-site mode.")
        return data
    


class LinkMonitoringSerializer(serializers.ModelSerializer):
    class Meta:
        model = LinkMonitoring
        fields = '__all__'
        read_only_fields = ('time_interval', 'retry_times', 'custom_command')

    def validate(self, data):

        # Ensure custom_command is set when time_out_action is custom
        if data.get('time_out_action') == 'custom' and not data.get('custom_command'):
            raise serializers.ValidationError({
                'custom_command': 'This field is required when time_out_action is custom.'
            })
        return data
    


class QOSPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = QOSPolicy
        fields = '__all__'

    def validate(self, data):
        # Rely on model.clean for validation
        return data





class FullMeshSerializer(serializers.ModelSerializer):
    class Meta:
        model = FullMesh
        fields = [
            'id', 'organization', 'created_by',
            'name', 'description', 'is_enabled',
            'members',  # JSON list of device rows
            'ike_version','ike_encryption_algorithm','ike_integrity_algorithm',
            'ike_diffie_hellman_group','ike_key_lifetime',
            'esp_version','esp_encryption_algorithm','esp_integrity_algorithm',
            'esp_diffie_hellman_group','esp_key_lifetime',
            'dpdaction','ipcomp','pre_shared_key',
            'created_at','updated_at',
        ]
        read_only_fields = ['id', 'organization', 'created_by', 'created_at', 'updated_at']

# class PairRowSerializer(serializers.Serializer):
#     # matches your CSV shape
#     num = serializers.IntegerField(source="#")
#     device_a = serializers.CharField(source="Device A")
#     wan_a = serializers.CharField(source="WAN A")
#     subnet_a = serializers.CharField(source="Subnet A")
#     device_b = serializers.CharField(source="Device B")
#     wan_b = serializers.CharField(source="WAN B")
#     subnet_b = serializers.CharField(source="Subnet B")
#     status = serializers.CharField(source="Status")
#     last_pushed = serializers.CharField(source="Last Pushed", allow_null=True, required=False)