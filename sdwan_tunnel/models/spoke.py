from django.core.exceptions import ValidationError
from django.db import models,transaction
from openwisp_controller.config.models import Config as Device
from openwisp_controller.config.models import Config as DeviceData

from openwisp_users.models import OrganizationUser
from openwisp_users.models import Organization
import ipaddress
from django.db.models import Q
from django.contrib.auth import get_user_model
from sdwan_tunnel.models.hub import Hub  # local import
from sdwan_tunnel.models.linkmonitoring import LinkMonitoring
from sdwan_tunnel.models.pathlabel import PathLabel
from openwisp_ipam.models import Subnet
import logging
logger = logging.getLogger(__name__)
User = get_user_model()

class Spoke(models.Model):
    
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("active", "Active"),
        ("error", "Error"),
        ("rolled_back", "Rolled Back"),
    ]
    
    device = models.ForeignKey(
        Device,
        related_name='spoke_devices',
        on_delete=models.CASCADE,
    )
    hub_device = models.ForeignKey(
        Hub,
        related_name='hub_devices',
        on_delete=models.CASCADE,
    )
    link_monitor = models.ForeignKey(
        LinkMonitoring,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='link_spokes',
        help_text='Optional ICMP link monitoring config for this spoke'
    )
    # Optional Domain monitoring config
    domain_monitor = models.ForeignKey(
        LinkMonitoring,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='domain_spokes',
        help_text='Optional Domain monitoring config for this spoke'
    )
    path_labels = models.ManyToManyField(
        PathLabel,
        blank=True,
        related_name='spokes',
        help_text='Optional path labels for this spoke'
    )




    organization = models.ForeignKey(
     Organization, 
     on_delete=models.CASCADE, 
     null=True, blank=True, editable=False
     )
    created_by = models.ForeignKey(
        User, 
        null=True, blank=True, 
        on_delete=models.SET_NULL, 
        editable=False
    )
    # created_by = models.ForeignKey(OrganizationUser, on_delete=models.SET_NULL, null=True)
    local_ip = models.GenericIPAddressField(
        help_text='Management IP of local device',
        blank=True,
        null=True,
    )
    wan_ip = models.GenericIPAddressField(
        help_text='WAN IP of local device',
        blank=True,
        null=True,
    )
    subnet = models.CharField(
        max_length=64,
        blank=True,
        null=True, 
        help_text='Allocated Subnet for this tunnel' 
    )
    is_enabled = models.BooleanField(default=True, help_text="Toggle to enable/disable this tunnel")

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='pending')
    up_time = models.FloatField(
       blank=True,
        null=True,
    )
    latency = models.FloatField(
       blank=True,
        null=True, 
    )
    jitter = models.FloatField(
       blank=True,
        null=True,
    )
    packet_loss = models.FloatField(
        blank=True,
        null=True,
    )
    uuid = models.CharField(
        blank=True,
        max_length=64,
        unique=True,
        help_text='Unique identifier for this spoke tunnel'
    )
    last_push_message = models.TextField(null=True, blank=True)
    last_pushed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        
        constraints = [
       models.UniqueConstraint(
            fields=['device', 'wan_ip', 'subnet'],
            name='unique_subnet_per_device'
        )]

    def __str__(self):
        
        return str(self.device) 
    

    def clean(self):
        super().clean()
        from sdwan_tunnel.models.hub import Hub  # local import

        if Hub.objects.filter(local_device=self.device).exists() or \
           Spoke.objects.exclude(pk=self.pk).filter(device=self.device).exists():
            raise ValidationError({
                'device': f'Device {self.device} is already assigned.'
            })
        # Validate that 'subnet' (if set) is a proper CIDR
        if self.subnet:
            try:
                ipaddress.ip_network(self.subnet)
            except ValueError:
                raise ValidationError({
                    'subnet': 'Must be a valid CIDR, e.g. 192.168.1.0/24'
                })
            
        # Enforce exclusivity: only matching monitors based on check_type
        if self.link_monitor and self.link_monitor.check_type != 'icmp':
            raise ValidationError({'link_monitor': 'Selected config must have check_type="icmp"'})
        if self.domain_monitor and self.domain_monitor.check_type != 'domain':
            raise ValidationError({'domain_monitor': 'Selected config must have check_type="domain"'})


    def save(self, *args, **kwargs):
        
            # copy the device’s key into the spoke.uuid
        self.uuid = self.device.device.id
        # Auto-assign a /30 if no subnet has been provided
        
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
