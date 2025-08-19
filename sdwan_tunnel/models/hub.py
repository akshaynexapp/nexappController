from django.core.exceptions import ValidationError
from django.db import models,transaction
from openwisp_controller.config.models import Config as Device
from openwisp_users.models import OrganizationUser
from openwisp_users.models import Organization
import ipaddress
from django.db.models import Q
from sdwan_tunnel.models.pathlabel import PathLabel

import logging
from openwisp_ipam.models import Subnet
from django.contrib.auth import get_user_model
User = get_user_model()
logger = logging.getLogger(__name__)

class Hub(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("active", "Active"),
        ("error", "Error"),
        ("rolled_back", "Rolled Back"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("active", "Active"),
        ("error", "Error"),
        ("rolled_back", "Rolled Back"),
    ]
    IKE_VERSION_CHOICES = [
        ('ike',  'IKEV1 & IKEV2'),
        ('ikev1','IKEv1'),
        ('ikev2','IKEv2'),
    ]
    ESP_VERSION_CHOICES = [
        ('esp',  'ESP'),
        ('espv1','ESPv1'),
        ('espv2','ESPv2'),
    ]
    ENCRYPTION_CHOICES = [
        ('aes128','AES-128'),
        ('aes192','AES-192'),
        ('aes256','AES-256'),
        ('3des',  '3DES'),
        ('des',   'DES'),
    ]
    INTEGRITY_CHOICES = [
        ('md5',     'MD5'),
        ('sha1',    'SHA-1'),
        ('sha256',  'SHA-256'),
        ('sha384',  'SHA-384'),
        ('sha512',  'SHA-512'),
        ('aescmac', 'AES-CMAC'),
        ('aesxcbc','AES-XCBC'),
    ]
    DH_GROUP_CHOICES = [
        ('modp1024','MODP-1024'),
        ('modp1536','MODP-1536'),
        ('modp2048','MODP-2048'),
        ('modp3072','MODP-3072'),
        ('modp4096','MODP-4096'),
    ]
    DPD_ACTION_CHOICES = [
        ('restart', 'restart'),
        ('none',    'none'),
    ]
    FORCEENCAPS_CHOICES = [
        ('yes', 'Yes'),
        ('no',  'No'),
    ]
    local_device = models.ForeignKey(
        Device,
        related_name='hubs',
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=128, unique=True, default='Tunnel')
    # organization = models.ForeignKey(
    #     Organization,
    #     on_delete=models.CASCADE,
    #     related_name='hubs',
    #     help_text='Organization this hub belongs to',
    # )
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
    
    path_labels = models.ManyToManyField(
        PathLabel,
        blank=True,
        related_name='path_label_hub',
        help_text='Optional path labels for this spoke'
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
        blank=False,
        null=False,
        help_text='Allocated Subnet for this tunnel' 
    )
    is_enabled = models.BooleanField(default=True, help_text="Toggle to enable/disable this tunnel")

    # status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='pending')
    forceencaps = models.CharField(max_length=5, choices=FORCEENCAPS_CHOICES, default='pending')
    dpdaction = models.CharField(
        max_length=10,
        choices=DPD_ACTION_CHOICES,
        default='none',
        help_text="Dead‐Peer Detection action (restart|none)"
    )
    ipcomp = models.BooleanField(
        default=False,
        help_text="Enable IP compression"
    )
    # local_identifier    = models.CharField(max_length=64, default='@tun3.local')
    # remote_identifier   = models.CharField(max_length=64, default='@tun3.remote')

    # IKE fields
    ike_version                = models.CharField(max_length=6,  choices=IKE_VERSION_CHOICES,       default='ike')
    ike_encryption_algorithm   = models.CharField(max_length=7,  choices=ENCRYPTION_CHOICES,       default='aes128')
    ike_integrity_algorithm    = models.CharField(max_length=15, choices=INTEGRITY_CHOICES,        default='sha256')
    ike_diffie_hellman_group   = models.CharField(max_length=12, choices=DH_GROUP_CHOICES,          default='modp2048')
    ike_key_lifetime           = models.PositiveIntegerField(default=3600, help_text="Lifetime in seconds")

    # ESP fields
    esp_version                = models.CharField(max_length=6,  choices=ESP_VERSION_CHOICES,       default='esp')
    esp_encryption_algorithm   = models.CharField(max_length=7,  choices=ENCRYPTION_CHOICES,       default='aes128')
    esp_integrity_algorithm    = models.CharField(max_length=15, choices=INTEGRITY_CHOICES,        default='sha256')
    esp_diffie_hellman_group   = models.CharField(max_length=12, choices=DH_GROUP_CHOICES,          default='modp2048')
    esp_key_lifetime           = models.PositiveIntegerField(default=3600, help_text="Lifetime in seconds")
    pre_shared_key = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        help_text='Persisted IPsec pre-shared key'
    )
    uuid = models.CharField(
        blank=True,
        max_length=64,
        unique=True,
        help_text='Unique identifier for this spoke tunnel'
    )
    last_pushed_at = models.DateTimeField(null=True, blank=True)
    last_config_hash = models.CharField(max_length=64, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_config_payload = models.JSONField(null=True, blank=True)

    class Meta:
        
        constraints = [
            models.UniqueConstraint(fields=['local_device', 'name'], name='unique_tunnel_per_device')
        ]

    def __str__(self):
        
        return str(self.local_device)

    def clean(self):
        super().clean()
    # local import, only at runtime
        from sdwan_tunnel.models.spoke import Spoke
        if Spoke.objects.filter(device=self.local_device).exists() or \
           Hub.objects.exclude(pk=self.pk).filter(local_device=self.local_device).exists():
            raise ValidationError({
                'local_device': f'Device {self.local_device} is already assigned.'
            })
        # Validate that 'subnet' (if set) is a proper CIDR
        if self.subnet:
            try:
                ipaddress.ip_network(self.subnet)
            except ValueError:
                raise ValidationError({
                    'subnet': 'Must be a valid CIDR, e.g. 192.168.1.0/24'
                })
            
        if not self.subnet:
            raise ValidationError({
                'subnet': 'Allocated Subnet is required for this tunnel.'
            })

    def save(self, *args, **kwargs):
        
            # copy the device’s key into the spoke.uuid
        self.uuid = self.local_device.device.id
        # Auto-assign a /30 if no subnet has been provided
        # if not self.subnet:
        #     self.subnet = self._auto_assign_subnet()
        is_new = self.pk is None
        super().save(*args, **kwargs)
        # enqueue exactly once if still blank
        

    
    def _format_ike(self):
        return f"{self.ike_encryption_algorithm}-{self.ike_integrity_algorithm}-{self.ike_diffie_hellman_group}"

    def _format_esp(self):
        return f"{self.esp_encryption_algorithm}-{self.esp_integrity_algorithm}"
   
