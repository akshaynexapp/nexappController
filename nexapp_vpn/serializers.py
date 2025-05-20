# serializer.py
 
from rest_framework import serializers
from .models import (
    Tunnel, Device,
    TunnelStatusLog,
    TunnelConfigHistory,
    TunnelHealthMetric,
    DevicePeer
)
 
class TunnelSerializer(serializers.ModelSerializer):
    device_b = serializers.PrimaryKeyRelatedField(
        queryset=Device.objects.all(),
        many=True,
        required=False
    )
 
    class Meta:
        model = Tunnel
        fields = '__all__'
 
    def validate(self, data):
        device_a = data.get('device_a')
        device_b = data.get('device_b')
        org = data.get('organization')
 
        if device_a and device_a.organization != org:
            raise serializers.ValidationError("Device A must belong to the selected organization.")
 
        if device_b:
            for device in device_b:
                if device.organization != org:
                    raise serializers.ValidationError(f"Device B '{device}' is not in the same organization.")
 
        if device_a and device_b and device_a in device_b:
            raise serializers.ValidationError("Device A cannot also be selected in Device B.")
 
        return data
 
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['config_preview'] = instance.generate_ipsec_conf()
        return data
 
 
class TunnelStatusLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TunnelStatusLog
        fields = '__all__'
 
 
class TunnelConfigHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TunnelConfigHistory
        fields = '__all__'
 
 
class TunnelHealthMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = TunnelHealthMetric
        fields = '__all__'
 
 
class DevicePeerSerializer(serializers.ModelSerializer):
    class Meta:
        model = DevicePeer
        fields = '__all__'
 