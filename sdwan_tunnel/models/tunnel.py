# sdwan_tunnel/models/tunnel.py

from django.db import models
from django import forms

from django.contrib.auth import get_user_model
from django.db.models import PROTECT
from openwisp_users.models import Organization


from openwisp_controller.config.models import Config as Device

from openwisp_controller.config.models import Template  # updated import for config templates
from jinja2 import Template as JinjaTemplate

from sdwan_tunnel.protocols.ipsec.handlers.site_to_site import deploy_site_to_site , rollback_site_to_site
from sdwan_tunnel.services.rollback_manager import rollback_device
from sdwan_tunnel.utils.logging_utils import structured_log
from django.core.exceptions import ValidationError
import ipaddress
from django.db.models import Q
from sdwan_tunnel.protocols.ipsec.client import get_ip_config_by_mgmt_ip , fetch_management_ips_by_names
from openwisp_ipam.models import Subnet
from sdwan_tunnel.protocols.ipsec.handlers.hub_spoke import deploy_hub_and_spoke

User = get_user_model()

class Tunnel(models.Model):
    """Core SD-WAN Tunnel configuration."""
    VPN_TYPE_CHOICES = [
        ('ipsec', 'IPsec'),
        ('wireguard', 'WireGuard'),
        ('openvpn', 'OpenVPN'),
        ('vxlan', 'VXLAN'),
    ]
    MODE_CHOICES = [
        ('site_to_site', 'Site-to-Site'),
        # ('hub_spoke', 'Hub & Spoke'),
        ('full_mesh', 'Full Mesh'),
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
 # organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=128, default='Tunnel')
    vpn_type = models.CharField(max_length=20, choices=VPN_TYPE_CHOICES)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES)
    # template = models.ForeignKey(Template, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='pending')
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    last_pushed_at = models.DateTimeField(null=True, blank=True)
    last_config_hash = models.CharField(max_length=64, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # device_a = models.ForeignKey(Active_devices, on_delete=models.SET_NULL, null=True, blank=True, related_name='as_device_a')
    device_a = models.ForeignKey(Device, on_delete=models.CASCADE, null=True, blank=True, related_name='as_device_a')
    device_b = models.ForeignKey(Device, on_delete=models.CASCADE, null=True, blank=True, related_name='as_device_b')
    last_config_payload = models.JSONField(null=True, blank=True)
    device_a_wan_ip = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        help_text='Allocated wan IP for device A'
    )
    device_a_subnet = models.CharField(
        max_length=64,
        blank=True,
        null=True, 
        help_text='Allocated Subnet for device A'
    )
   
    device_b_wan_ip = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        help_text='Allocated IP for device B'
    )
    device_b_subnet = models.CharField(
        max_length=64,
        blank=True,
        null=True, 
        help_text='Allocated Subnet for device B'
    )
    is_enabled          = models.BooleanField(default=True, help_text="Toggle to enable/disable this tunnel")
    # local_identifier    = models.CharField(max_length=64, default='@tun3.local')
    # remote_identifier   = models.CharField(max_length=64, default='@tun3.remote')
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
    last_push_message = models.TextField(null=True, blank=True)

    pre_shared_key = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        help_text='Persisted IPsec pre-shared key'
    )
    local_ip_a = models.GenericIPAddressField(
        help_text='Management IP of local device A',
        blank=True,
        null=True,
    )
    local_ip_b = models.GenericIPAddressField(
        help_text='Management IP of local device B',
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
    uuid_b = models.CharField(
        blank=True,
        max_length=64,
        unique=True,
        help_text='Unique identifier for device B',
    )
    uuid_a = models.CharField(
        blank=True,
        max_length=64,
        unique=True,
        help_text='Unique identifier for device A',
    )
 
    # … rest of your model …
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

    class Meta:
        
        constraints = [
            models.UniqueConstraint(fields=['device_a', 'name'], name='unique_tunnel_per_device_a')
        ]
    
        
    

    def __str__(self):
        return self.name
    
    def clean(self):
         super().clean()

         if self.device_a_id and self.device_b_id and self.device_a_id == self.device_b_id:
            raise ValidationError({
                'device_b': 'Device B must be different from Device A.',
            })
         # 1) CIDR syntax checks (always)
         for field in ('device_a_subnet', 'device_b_subnet'):
             cidr = getattr(self, field)
             if cidr:
                 try:
                     ipaddress.ip_network(cidr)
                 except ValueError:
                     raise ValidationError({field: 'Must be a valid CIDR, e.g. 192.168.1.0/24'})
  
         # 2) Skip all the M2M checks on a brand-new object (no PK yet)
         if self._state.adding:
             return
  
         # 3) Only enforce “exactly one remote” when in site-to-site mode
         if self.mode == 'site_to_site':
             
             # 4) Prevent duplicate tunnels on the same pair
             if Tunnel.objects.filter(
                    mode='site_to_site',
                    device_a=self.device_a,
                    device_b=self.device_b
                ).exclude(pk=self.pk).exists():
                 raise ValidationError(
                     'A tunnel between these devices already exists; please modify it.'
                )
    
       
    def save(self, *args, **kwargs):
        # if not self.device_a_subnet:
        #     self.device_a_subnet = self._auto_assign_subnet()
        # if not self.device_b_subnet:
        #     self.device_b_subnet = self._auto_assign_subnet()
        # if not self.device_a_wan_ip:
        #     self.device_a_wan_ip = self._get_wan_ip_a()
        # # if not self.device_b_wan_ip:
        #     self.device_b_wan_ip = self._get_wan_ip_b()
        self.uuid_a = self.device_a.device.id
        self.uuid_b = self.device_b.device.id
        super().save(*args, **kwargs)


    def _format_ike(self):
        return f"{self.ike_encryption_algorithm}-{self.ike_integrity_algorithm}-{self.ike_diffie_hellman_group}"

    def _format_esp(self):
        return f"{self.esp_encryption_algorithm}-{self.esp_integrity_algorithm}"
   

    # def _get_wan_ip_a(self):
    #     """
    #     Fetch the WAN IP of device A via its management API.
    #     """
    #     device_names = [self.device_a.name]
    #     mgmt_map = fetch_management_ips_by_names(device_names)
    #     mgmt_ip = mgmt_map.get(self.device_a.name)
    #     if not mgmt_ip:
    #         raise ValidationError('Management IP not found for device A.')

    #     response = get_ip_config_by_mgmt_ip(mgmt_ip)
    #     data = response.get('data', {})
    #     local_wan_ip = data.get('local_wan_ip')
    #     if not local_wan_ip:
    #         raise ValidationError(f'Failed to fetch WAN IP: {local_wan_ip}')
    #     return local_wan_ip
    
  

    # def _auto_assign_subnet(self):
    #     """
    #     Auto-assign a /30 subnet via IPAM:
    #     - Parent pool = Subnet objects with master_subnet=None
    #     - Scoped to either the tunnel’s organization or global pools
    #     """
    #     # 1) find all top-level pools for this org or global
    #     pool_qs = Subnet.objects.filter(master_subnet__isnull=True).filter(
    #         Q(organization=self.organization) 
    #     )
    #     pool = pool_qs.first()
    #     if not pool:
    #         raise ValidationError(
    #             f'No IPAM Subnet pool (master_subnet=None) available for org {self.organization}'
    #         )
    #     # 2) compute used /30s under this pool for this org
    #     used = [
    #         ipaddress.ip_network(child.subnet)
    #         for child in pool.child_subnet_set.filter(organization=self.organization)
    #     ]
    #     parent_net = ipaddress.ip_network(pool.subnet)
    #     # 3) iterate candidates
    #     for candidate in parent_net.subnets(new_prefix=30):
    #         if all(not candidate.overlaps(u) for u in used):
    #             # 4) reserve it by creating a child Subnet
    #             new_sub = Subnet(
    #                 name=f'{self.name}-{candidate}',
    #                 subnet=str(candidate),
    #                 master_subnet=pool,
    #                 organization=self.organization
    #             )
    #             new_sub.full_clean()
    #             new_sub.save()
    #             return str(candidate)
    #     # 5) no room left
    #     raise ValidationError(f'No free /30 prefixes left in IPAM pool {pool.subnet}')


    def push_to_agent(self,job_id=None, full_replace=False):
        """
        Top-level push entrypoint for this tunnel.
        Delegates to the Site-to-Site IPsec handler and handles history/status.
        """
     
 
        try:
            # Only support Phase 1: IPsec Site-to-Site
            if self.vpn_type == 'ipsec' and self.mode == 'site_to_site':
                # Call the Phase 1 handler
                result = deploy_site_to_site(self.id,job_id=job_id, full_replace=full_replace)

            # if self.vpn_type == 'ipsec' and self.mode == 'hub_spoke':
            #     result = deploy_hub_and_spoke(self.id, full_replace=full_replace)
            
            
            return result
 
        except Exception as e:
            # Log error, mark status, and attempt rollback
           
            self.status = 'error'
            self.save(update_fields=['status'])
            
            try:
                rb = rollback_device(self, self.vpn_type)
                
            except Exception:
                pass
            return {'status': 'error', 'message': str(e)}
    


    def rollback_last_config(self):
        """
        Rollback the last pushed configuration.
        """
        try:
            # Call the rollback handler
            result = rollback_site_to_site(self.id, full_replace=False)
            return {'status': 'success', 'message': 'Rollback successful.'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}