# ONE MODEL ONLY: FullMesh
from itertools import combinations
import ipaddress

from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q
from openwisp_users.models import Organization
from openwisp_controller.config.models import Config as Device
from openwisp_controller.config.models import Config as ConfigModel, Device as OwDevice

User = get_user_model()

# ---- Choices (same as your policy fields) ----
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
    ('md5','MD5'), ('sha1','SHA-1'), ('sha256','SHA-256'),
    ('sha384','SHA-384'), ('sha512','SHA-512'),
    ('aescmac','AES-CMAC'), ('aesxcbc','AES-XCBC'),
]
DH_GROUP_CHOICES = [
    ('modp1024','MODP-1024'), ('modp1536','MODP-1536'),
    ('modp2048','MODP-2048'), ('modp3072','MODP-3072'), ('modp4096','MODP-4096'),
]
DPD_ACTION_CHOICES = [('restart', 'restart'), ('none', 'none')]

STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('active', 'Active'),
    ('error', 'Error'),
    ('rolled_back', 'Rolled Back'),
]

class FullMesh(models.Model):
    """
    Single object holding:
      - header (name, description, org, created_by, is_enabled)
      - global IPsec policy (IKE/ESP/DPD/IPComp + optional pre_shared_key)
      - device rows as JSON (table you edit on one page)
    Pairs are computed on the fly from the JSON (not stored).
    """
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, null=True, blank=True, editable=False
    )
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, editable=False
    )

    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True)
    is_enabled = models.BooleanField(default=True)

    # Global IPsec policy (identical across the mesh)
    ike_version              = models.CharField(max_length=6,  choices=IKE_VERSION_CHOICES, default='ike')
    ike_encryption_algorithm = models.CharField(max_length=7,  choices=ENCRYPTION_CHOICES,   default='aes128')
    ike_integrity_algorithm  = models.CharField(max_length=15, choices=INTEGRITY_CHOICES,    default='sha256')
    ike_diffie_hellman_group = models.CharField(max_length=12, choices=DH_GROUP_CHOICES,     default='modp2048')
    ike_key_lifetime         = models.PositiveIntegerField(default=3600)

    esp_version              = models.CharField(max_length=6,  choices=ESP_VERSION_CHOICES, default='esp')
    esp_encryption_algorithm = models.CharField(max_length=7,  choices=ENCRYPTION_CHOICES,   default='aes128')
    esp_integrity_algorithm  = models.CharField(max_length=15, choices=INTEGRITY_CHOICES,    default='sha256')
    esp_diffie_hellman_group = models.CharField(max_length=12, choices=DH_GROUP_CHOICES,     default='modp2048')
    esp_key_lifetime         = models.PositiveIntegerField(default=3600)

    dpdaction = models.CharField(max_length=10, choices=DPD_ACTION_CHOICES, default='none')
    ipcomp    = models.BooleanField(default=False)

    # Optional shared PSK for all pairs (leave blank if using certs)
    pre_shared_key = models.CharField(max_length=128, blank=True, null=True)

    # TABLE OF DEVICES (one-page edit): list of rows like
    # [
    #   {
    #     "device": "<Device.pk>",        # REQUIRED (string/uuid/int)
    #     "uuid": "optional external id",
    #     "subnet": "10.10.11.0/24",
    #     "local_ip": "10.0.0.11",
    #     "wan_ip": "203.0.113.11",
    #     "is_enabled": true
    #   },
    #   ...
    # ]
    members = models.JSONField(default=list, help_text="List of device rows for this mesh.")

    # (Optional) rollup/ops fields if you want to show last deploy summary
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_sync_message = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    # ---------- Derived helpers ----------
    @property
    def enabled_members(self):
        return [m for m in self.members or [] if m.get('is_enabled', True)]

    @property
    def edges_count(self):
        n = len(self.enabled_members)
        return (n * (n - 1)) // 2

    def policy_dict(self):
        return {
            'ike_version': self.ike_version,
            'ike_encryption_algorithm': self.ike_encryption_algorithm,
            'ike_integrity_algorithm': self.ike_integrity_algorithm,
            'ike_diffie_hellman_group': self.ike_diffie_hellman_group,
            'ike_key_lifetime': self.ike_key_lifetime,
            'esp_version': self.esp_version,
            'esp_encryption_algorithm': self.esp_encryption_algorithm,
            'esp_integrity_algorithm': self.esp_integrity_algorithm,
            'esp_diffie_hellman_group': self.esp_diffie_hellman_group,
            'esp_key_lifetime': self.esp_key_lifetime,
            'dpdaction': self.dpdaction,
            'ipcomp': self.ipcomp,
            'pre_shared_key': self.pre_shared_key,
        }

    # Compute the A↔B table (like your CSV) without storing it
    def pair_table(self):
        """
        Returns a list of rows:
        [
          {'#': 1, 'Device A': name, 'WAN A': wan, 'Subnet A': subnet,
           'Device B': name, 'WAN B': wan, 'Subnet B': subnet,
           'Status': 'Pending', 'Last Pushed': None},
          ...
        ]
        """
        rows = []
        # Enrich members with Device objects & names
        enriched = []
        
        for m in self.enabled_members:
            dev_id = m.get('device')
            if not dev_id:
                continue
            name = None
            try:
                dev = Device.objects.get(pk=dev_id)
            except Device.DoesNotExist:
                # if device not found, show placeholder
                dev = None
            try:
                cfg = ConfigModel.objects.select_related('device').get(pk=dev_id)
                name = cfg.device.name if cfg.device_id else None
            except ConfigModel.DoesNotExist:
                pass

            if not name:
                try:
                    dev = OwDevice.objects.get(pk=dev_id)
                    name = dev.name
                except OwDevice.DoesNotExist:
                    name = str(dev_id)
            enriched.append({
                'device_obj': dev,
                'device_name': name,
                'wan_ip': m.get('wan_ip') or '',
                'subnet': m.get('subnet') or '',
                'local_ip': m.get('local_ip') or '',
            })
            

        idx = 1
        for a, b in combinations(enriched, 2):
            rows.append({
                '#': idx,
                'Device A': a['device_name'],
                'WAN A': a['wan_ip'],
                'Subnet A': a['subnet'],
                'Device B': b['device_name'],
                'WAN B': b['wan_ip'],
                'Subnet B': b['subnet'],
                'Status': 'Pending',
                'Last Pushed': None,
            })
            idx += 1
        return rows

    # ---------- Validation ----------
    def clean(self):
        errs = {}

        # at least 2 enabled members
        em = self.enabled_members
        if len(em) < 2:
            errs['members'] = 'A full mesh must have at least 2 enabled devices.'

        # validate members shape & uniqueness of device
        seen = set()
        row_errs = []
        for i, m in enumerate(self.members or []):
            row_e = {}
            dev_pk = m.get('device')
            if not dev_pk:
                row_e['device'] = 'Device is required.'
            else:
                if dev_pk in seen:
                    row_e['device'] = 'Duplicate device in mesh.'
                else:
                    seen.add(dev_pk)
                # check that device exists
                if not Device.objects.filter(pk=dev_pk).exists():
                    row_e['device'] = 'Device does not exist.'

            # basic ip/subnet checks (best-effort)
            subnet = m.get('subnet')
            if subnet:
                try:
                    ipaddress.ip_network(subnet, strict=False)
                except Exception:
                    row_e['subnet'] = 'Invalid subnet (e.g., 10.10.11.0/24).'
            for fld in ('local_ip', 'wan_ip'):
                val = m.get(fld)
                if val:
                    try:
                        ipaddress.ip_address(val)
                    except Exception:
                        row_e[fld] = f'Invalid IP address in {fld}.'

            if row_e:
                row_errs.append((i, row_e))

        if row_errs:
            # collapse row errors into members error
            errs['members'] = {'rows': row_errs}

        if errs:
            raise ValidationError(errs)

    # ---------- Optional: normalize before save ----------
    def save(self, *args, **kwargs):
        # You can normalize member data here if needed (e.g., coerce types)
        super().save(*args, **kwargs)
