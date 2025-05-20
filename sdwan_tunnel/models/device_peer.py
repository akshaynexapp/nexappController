
# sdwan_tunnel/models/device_peer.py
"""
Associates tunnels to multiple device endpoints with roles and IPs.
Fields:
- FK to Tunnel, local and peer device names, management IPs, subnet, roles
"""
from django.db import models
from openwisp_controller.config.models import Config as Device
from .tunnel import Tunnel


class DevicePeer(models.Model):
    ROLE_CHOICES = [('hub','Hub'),('spoke','Spoke')]
    tunnel = models.ForeignKey(Tunnel, related_name='device_peers', on_delete=models.CASCADE)
    local_device = models.ForeignKey(Device, related_name='local_peers', on_delete=models.CASCADE)
    peer_device = models.ForeignKey(Device, related_name='peer_peers', on_delete=models.CASCADE)
    local_ip = models.GenericIPAddressField(help_text='Management IP of local device')
    peer_ip = models.GenericIPAddressField(help_text='Management IP of peer device')
    link_subnet = models.CharField(max_length=64, help_text='Subnet for link')
    local_role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    peer_role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('tunnel','local_device','peer_device')
        verbose_name = 'Device Peer'
        verbose_name_plural = 'Device Peers'

    def __str__(self):
        return f"{self.local_device.name} <-> {self.peer_device.name} ({self.tunnel.name})"