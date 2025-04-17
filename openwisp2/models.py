from django.db import models
from openwisp_controller.config.models import Config as Device

class TunnelTemplate(models.Model):
    VPN_TYPES = [
        ("ipsec", "IPsec"),
        ("openvpn", "OpenVPN"),
        ("vxlan", "VXLAN"),
    ]
    MODES = [
        ("site_to_site", "Site-to-Site"),
        ("hub_spoke", "Hub & Spoke"),
        ("full_mesh", "Full Mesh"),
    ]

    name = models.CharField(max_length=100, unique=True)
    vpn_type = models.CharField(max_length=20, choices=VPN_TYPES)
    mode = models.CharField(max_length=20, choices=MODES)
    config_template = models.TextField(help_text="Jinja2-style config template")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.vpn_type})"


class Tunnel(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("active", "Active"),
        ("error", "Error"),
    ]

    device_a = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='tunnels_as_a')
    device_b = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='tunnels_as_b')
    vpn_type = models.CharField(max_length=20, choices=TunnelTemplate.VPN_TYPES)
    mode = models.CharField(max_length=20, choices=TunnelTemplate.MODES)
    template = models.ForeignKey(TunnelTemplate, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    last_health_check = models.DateTimeField(null=True, blank=True)
    latency = models.FloatField(null=True, blank=True)
    packet_loss = models.FloatField(null=True, blank=True)
    jitter = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.device_a.name} ↔ {self.device_b.name} ({self.vpn_type})"


class DevicePeer(models.Model):
    ROLE_CHOICES = [("hub", "Hub"), ("spoke", "Spoke")]

    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    tunnel = models.ForeignKey(Tunnel, on_delete=models.CASCADE, related_name="peers")

    def __str__(self):
        return f"{self.device.name} as {self.role}"
