
from django.db import models
from rest_framework import serializers
from openwisp_users.models import OrganizationUser
from django.utils.timezone import now
from openwisp_users.models import Organization
from openwisp_controller.config.models import Config as Device
from openwisp_controller.config.models import Template  # updated import for config templates
from jinja2 import Template as JinjaTemplate
import requests
import hashlib
import logging

import secrets
import json
import socket
import time

from django.core.serializers.json import DjangoJSONEncoder
from django.core.mail import mail_admins
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from ipaddress import ip_network, ip_address
from django.conf import settings
from django.core.exceptions import ValidationError
import requests
from django.http import JsonResponse
from django.core.cache import cache 
from rest_framework.authtoken.models import Token
 
# Note: OpenWISP API requires 'Authorization: Token <token>' header, not X-CSRFTOKEN
 
 
# OpenWISP Controller API endpoint
CONTROLLER_API_URL = "https://3.6.121.36/api/v1/controller/device/"
ONLINE_API_URL = 'https://3.6.121.36/api/v1/monitoring/device/'
TOKEN_API_URL = "https://3.6.121.36/api/v1/users/token/"
USERNAME = "admin"
PASSWORD = "Nexapp@123"
 


 
def get_bearer_token():
    try:
        response = requests.post(
            TOKEN_API_URL,
            data={"username": USERNAME, "password": PASSWORD},
            verify=False ,timeout=10
        )
        response.raise_for_status()
        return response.json().get("token")
    except Exception as e:
        print(f"[API ERROR] Failed to retrieve bearer token: {e}")
        return None



def fetch_online_devices_by_names(device_names):
    print(f"[DEBUG] Requesting devices for names: {device_names}")
    token = get_bearer_token()
    if not token:
       token = '80ee082483ee2a41d520909e571a3970f06d5907'
        

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(ONLINE_API_URL, headers=headers, verify=False, timeout=10)
        print(f"[DEBUG] Response URL: {response.url}")
        print(f"[DEBUG] Status Code: {response.status_code}")
        response.raise_for_status()

        all_devices = response.json().get("results", [])
        # Keep only devices whose name is in device_names AND monitoring.status == "ok"
        filtered_devices = [
            d for d in all_devices
            if d.get("name") in device_names
               and d.get("monitoring", {}).get("status") == "ok"
        ]
        print(f"[DEBUG] Found {len(filtered_devices)} device(s) with status 'ok'")

        # Print each matched device's name and its monitoring status
        for dev in filtered_devices:
            name = dev.get("name")
            status = dev.get("monitoring", {}).get("status")
            print(f"Device '{name}' monitoring status: '{status}'")

        return filtered_devices

    except requests.RequestException as e:
        print(f"[API ERROR] Failed to fetch devices: {e}")
        return []



def fetch_management_ips_by_names(device_names):
    print(f"[DEBUG] Requesting management IPs for device names: {device_names}")
    token = get_bearer_token()
    if not token:
        token = '80ee082483ee2a41d520909e571a3970f06d5907'
 
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
 
    try:
        response = requests.get(CONTROLLER_API_URL, headers=headers, verify=False,timeout=15)
        print(f"[DEBUG] Response URL: {response.url}")
        print(f"[DEBUG] Status Code: {response.status_code}")
        response.raise_for_status()
        all_devices = response.json().get("results", [])
 
        filtered_devices = [d for d in all_devices if d.get("name")  in device_names]
        print(f"[DEBUG] Filtered to {len(filtered_devices)} matched device(s)")
        for dev in filtered_devices:
            print(f"[DEBUG] Matched Name: {dev['name']} | Management IP: {dev.get('management_ip')}")
 
        return {
            d["name"]: d.get("management_ip")
            for d in filtered_devices
        }
    except Exception as e:
        print(f"[API ERROR] Failed to fetch IPs: {e}")
        return {}
 
def get_ipsec_config_by_mgmt_ip(mgmt_ip):
        url = f"https://{mgmt_ip}/api-new/ipsec"
        payload = {
            "method": "get-config",
            "payload": {}
        }
        try:
            response = requests.post(url, json=payload, verify=False, timeout=15)
            response.raise_for_status()
            data = response.json()
            print(f"[DEBUG] Received IPSec config from {mgmt_ip}: {data}")
            return data
        except Exception as e:
           print(f"[API ERROR] Failed to fetch IPSec config from {mgmt_ip}: {e}")
           return {"status": "error", "message": str(e)}



def push_ipsec_config_by_mgmt_ip(mgmt_ip, config_data):
    url = f"https://{mgmt_ip}/api-new/ipsec"
    payload = {
        "method": "add-tunnel",
        "payload": config_data
    }
    try:
        response = requests.post(url, json=payload, verify=False, timeout=15)
        response.raise_for_status()
        result = response.json()
        print(f"[DEBUG] Successfully pushed IPSec config to {mgmt_ip}: {result}")
        return result
    except Exception as e:
        print(f"[API ERROR] Failed to push IPSec config to {mgmt_ip}: {e}")
        return {"status": "error", "message": str(e)}
 



class TunnelQuerySet(models.QuerySet):
    def for_organization(self, organization):
        return self.filter(organization=organization)

    def online_devices_for_org(self, organization):
        return Device.objects.filter(organization=organization, status='online')

    def available_device_b_choices(self, organization, device_a):
        return Device.objects.filter(organization=organization, status='online').exclude(id=device_a.id if device_a else None)

VPN_TYPE_CHOICES = [
    ("ipsec", "IPsec"),
    ("openvpn", "OpenVPN"),
    ("vxlan", "VXLAN"),
]

MODE_CHOICES = [
    ("site_to_site", "Site-to-Site"),
    ("hub_spoke", "Hub & Spoke"),
    ("full_mesh", "Full Mesh"),
]

class Tunnel(models.Model):

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['device_a', 'name'], name='unique_tunnel_per_device_a')
        ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("active", "Active"),
        ("error", "Error"),
    ]
    IKE_VERSION_CHOICES = [
        ('ikev',  'IKEV1 & IKEV2'),
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

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=128, default='Tunnel')
    vpn_type = models.CharField(max_length=20, choices=VPN_TYPE_CHOICES)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES)
    template = models.ForeignKey(Template, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='pending')
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    last_pushed_at = models.DateTimeField(null=True, blank=True)
    last_config_hash = models.CharField(max_length=64, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    device_a = models.ForeignKey(Device, on_delete=models.SET_NULL, null=True, blank=True, related_name='as_device_a')
    device_b = models.ManyToManyField(Device, blank=True, related_name='as_device_b')
    is_enabled          = models.BooleanField(default=True, help_text="Toggle to enable/disable this tunnel")
    local_identifier    = models.CharField(max_length=64, default='@tun3.local')
    remote_identifier   = models.CharField(max_length=64, default='@tun3.remote')
    
    # choice constants
    
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

    objects = TunnelQuerySet.as_manager()

    def __str__(self):
        return self.name
    
 


    def save(self, *args, **kwargs):
        logger = logging.getLogger(__name__)
        try:
            logger.info("Running full_clean...")
            self.full_clean()
    
            logger.info("Assigning subnet if needed...")
    
            logger.info("Saving Tunnel...")
            super().save(*args, **kwargs)
            # result = self.push_ipsec_config()
        except Exception as e:
            logger.exception("Tunnel save failed with exception:")
            raise

 
    def export_json(self):
        return json.dumps({
            "name": self.name,
            "vpn_type": self.vpn_type,
            "mode": self.mode,
            "status": self.status,
            # "psk": self.psk,
            "template": str(self.template),
            "template_id": str(self.template.id) if self.template else None,
            "device_a_id": str(self.device_a.id) if self.device_a else None,
            "device_b_ids": [str(d.id) for d in self.device_b.all()],
            # "device_a_subnet": self.device_a_subnet,
            # "spoke_lan_subnet": self.spoke_lan_subnet,
            "last_pushed_at": str(self.last_pushed_at) if self.last_pushed_at else None
        }, cls=DjangoJSONEncoder)
    
  
   
    def push_site_to_site_ipsec_config(self):
    
        device_names = [self.device_a.name] + [d.name for d in self.device_b.all()]
        online_map = fetch_online_devices_by_names(device_names)
        ip_map = fetch_management_ips_by_names(device_names)
        if not online_map:
            return {"status": "error", "message": "device is not omline"}
        hub_ip = ip_map.get(self.device_a.name)
        if not hub_ip:
            print( "Hub IP not found")
     
        # Step 1: Send get-config request to device_a (Hub) to retrieve IP/subnet info
        hub_config = get_ipsec_config_by_mgmt_ip(hub_ip).get("data", {})
        if hub_config.get("code") !=200:
            print( "Hub config not found")

            
        results = []
        print(f"[DEBUG] Spoke IP: {hub_config}")

        # Step 2: Send get-config request to each device_b (Spoke) to retrieve IP/subnet info
        for spoke in self.device_b.all():
            spoke_ip = ip_map.get(spoke.name)
            # if not spoke_ip:
            #     results.append({"device": spoke.name, "status": "error", "message": "No management IP"})
            #     continue
            print(f"[DEBUG] Spoke IP: {spoke_ip}")
            spoke_config = get_ipsec_config_by_mgmt_ip(spoke_ip).get("data", {})
            if spoke_config.get("code") !=200:
                print("spoke config not found")
            # Step 3: Construct set-config payload for device_a (Hub)
            hub_payload = {
               
                "ns_name": self.name,
                "ike": {
                  "hash_algorithm": self.ike_integrity_algorithm,
                  "encryption_algorithm": self.ike_encryption_algorithm,
                  "dh_group": self.ike_diffie_hellman_group,
                  "rekeytime": self.ike_key_lifetime
                },
                "esp": {
                  "hash_algorithm": self.esp_integrity_algorithm,
                  "encryption_algorithm": self.esp_encryption_algorithm,
                  "dh_group": self.esp_diffie_hellman_group,
                  "rekeytime": self.esp_key_lifetime
                },
                "ipcomp": "true",
                "enabled": "1",
                "dpdaction": "none",
                "keyexchange": self.ike_version,
                # "remote_subnet": [self.remote_subnet],
                # "local_subnet":  [self.local_subnet],
                "remote_subnet": ["192.168.25.0/24"],
                "local_subnet": ["192.168.120.0/24"],
                "gateway": "192.168.2.194",
                "local_identifier": self.local_identifier,
                "remote_identifier": self.remote_identifier,
                "local_ip": hub_ip,
                "pre_shared_key": "qL7UKwQl4HbYzmZwT0Eyzu4txAPZ3avgiV8yGRsh35LO9d81MhDVV0AqHNs51Tbr0HNxrb/gahhnOW17Avf6aB0V"
            }
     
            # Step 4: Construct set-config payload for device_b (Spoke)
            spoke_payload = {
               
                "ns_name": self.name,
                "ike": {
                  "hash_algorithm": self.ike_integrity_algorithm,
                  "encryption_algorithm": self.ike_encryption_algorithm,
                  "dh_group": self.ike_diffie_hellman_group,
                  "rekeytime": self.ike_key_lifetime
                },
                "esp": {
                  "hash_algorithm": self.esp_integrity_algorithm,
                  "encryption_algorithm": self.esp_encryption_algorithm,
                  "dh_group": self.esp_diffie_hellman_group,
                  "rekeytime": self.esp_key_lifetime
                },
                "ipcomp": "true",
                "enabled": "1",
                "dpdaction": "none",
                "keyexchange": self.ike_version,
                "remote_subnet": ["192.168.50.0/24"],
                "local_subnet": ["192.168.150.0/24"],
                "gateway": "192.168.2.194",
                "local_identifier": self.local_identifier,
                "remote_identifier": self.remote_identifier,
                "local_ip": spoke_ip,
                "pre_shared_key": "qL7UKwQl4HbYzmZwT0Eyzu4txAPZ3avgiV8yGRsh35LO9d81MhDVV0AqHNs51Tbr0HNxrb/gahhnOW17Avf6aB0V"
            }
     
            # Step 5: Push set-config to device_a (Hub) with device_b info
            hub_result = push_ipsec_config_by_mgmt_ip(hub_ip, hub_payload)
     
            # Step 6: Push set-config to device_b (Spoke) with device_a info
            spoke_result = push_ipsec_config_by_mgmt_ip(spoke_ip, spoke_payload)
     
            # Log results and push status update
            if hub_result.get("status") != "error" and spoke_result.get("status") != "error":
                self.status = 'active'
                self.last_pushed_at = timezone.now()
            else:
                self.status = 'error'
     
            self.save()
     
            TunnelStatusLog.objects.create(
                tunnel=self,
                status=self.status,
                log=f"Site-to-Site IPSec push for {spoke.name}: Hub: {hub_result.get('status')}, Spoke: {spoke_result.get('status')}"
            )
     
            results.append({
                "device": spoke.name,
                "hub_result": hub_result,
                "spoke_result": spoke_result
            })
     
        return results
   
   
    # def push_site_to_site_ipsec_config(self):
    
    #     device_names = [self.device_a.name] + [d.name for d in self.device_b.all()]
    #     online_map = fetch_online_devices_by_names(device_names)
    #     ip_map = fetch_management_ips_by_names(device_names)
    #     if not online_map:
    #         return {"status": "error", "message": "device is not omline"}
       
       
    #     hub_ip = ip_map.get(self.device_a.name)
    #     if not hub_ip:
    #         print( "Hub IP not found")
     
    #     # Step 1: Send get-config request to device_a (Hub) to retrieve IP/subnet info
    #     hub_config = get_ipsec_config_by_mgmt_ip(hub_ip).get("data", {})
    #     if hub_config.get("code") !=200:
    #         print( "Hub config not found")




    #     # hub_resp = get_ipsec_config_by_mgmt_ip(hub_ip)
    #     #     # If the helper itself failed (e.g. token error), it returns {"status":"error",...}
    #     # if hub_resp.get("status") == "error":
    #     #     return [{
    #     #         "device": self.device_a.name,
    #     #         "hub_result": hub_resp,
    #     #         "spoke_result": {"status":"skipped","message":"spoke not contacted"}
    #     #     }]
    #     # # If the HTTP call succeeded but the API code isn’t 200, bail
    #     # if hub_resp.get("code") != 200:
    #     #     return [{
    #     #         "device": self.device_a.name,
    #     #         "hub_result": {"status":"error","message":f"get-config code {hub_resp.get('code')}"},
    #     #         "spoke_result": {"status":"skipped","message":"spoke not contacted"}
    #     #     }]
    #     # hub_data = hub_resp["data"]
    
    #     # results = []
    #     # for spoke in self.device_b.all():
    #     #     spoke_ip = ip_map.get(spoke.name)
        
    #     #     print(f"[DEBUG] Spoke IP: {spoke_ip}")
    #     # # … repeat the same pattern for spoke …
    #     #     spoke_resp = get_ipsec_config_by_mgmt_ip(spoke_ip)
    #     #     if spoke_resp.get("status") == "error" or spoke_resp.get("code") != 200:
    #     #         results.append({
    #     #             "device": spoke.name,
    #     #             "hub_result": {"status":"skipped","message":"hub ok"},
    #     #             "spoke_result": spoke_resp if spoke_resp.get("status")=="error" 
    #     #                            else {"status":"error","message":f"code {spoke_resp.get('code')}"}
    #     #         })
    #     #         continue




            
    #     results = []
    #     print(f"[DEBUG] Spoke IP: {hub_config}")

    #     # Step 2: Send get-config request to each device_b (Spoke) to retrieve IP/subnet info
    #     for spoke in self.device_b.all():
    #         spoke_ip = ip_map.get(spoke.name)
    #         # if not spoke_ip:
    #         #     results.append({"device": spoke.name, "status": "error", "message": "No management IP"})
    #         #     continue
    #         print(f"[DEBUG] Spoke IP: {spoke_ip}")
    #         spoke_config = get_ipsec_config_by_mgmt_ip(spoke_ip).get("data", {})
    #         if spoke_config.get("code") !=200:
    #             print("spoke config not found")




    #         # Step 3: Construct set-config payload for device_a (Hub)
    #         hub_payload = {
               
    #             "ns_name": self.name,
    #             "ike": {
    #               "hash_algorithm": self.ike_integrity_algorithm,
    #               "encryption_algorithm": self.ike_encryption_algorithm,
    #               "dh_group": self.ike_diffie_hellman_group,
    #               "rekeytime": self.ike_key_lifetime
    #             },
    #             "esp": {
    #               "hash_algorithm": self.esp_integrity_algorithm,
    #               "encryption_algorithm": self.esp_encryption_algorithm,
    #               "dh_group": self.esp_diffie_hellman_group,
    #               "rekeytime": self.esp_key_lifetime
    #             },
    #             "ipcomp": "true",
    #             "enabled": "1",
    #             "dpdaction": "none",
    #             "keyexchange": self.ike_version,
    #             "remote_subnet": ["192.168.25.0/24"],
    #             "local_subnet": ["192.168.120.0/24"],
    #             "gateway": "192.168.2.194",
    #             "local_identifier": self.local_identifier,
    #             "remote_identifier": self.remote_identifier,
    #             "local_ip": hub_ip,
    #             "pre_shared_key": "qL7UKwQl4HbYzmZwT0Eyzu4txAPZ3avgiV8yGRsh35LO9d81MhDVV0AqHNs51Tbr0HNxrb/gahhnOW17Avf6aB0V"
    #         }
     
    #         # Step 4: Construct set-config payload for device_b (Spoke)
    #         spoke_payload = {
               
    #             "ns_name": self.name,
    #             "ike": {
    #               "hash_algorithm": self.ike_integrity_algorithm,
    #               "encryption_algorithm": self.ike_encryption_algorithm,
    #               "dh_group": self.ike_diffie_hellman_group,
    #               "rekeytime": self.ike_key_lifetime
    #             },
    #             "esp": {
    #               "hash_algorithm": self.esp_integrity_algorithm,
    #               "encryption_algorithm": self.esp_encryption_algorithm,
    #               "dh_group": self.esp_diffie_hellman_group,
    #               "rekeytime": self.esp_key_lifetime
    #             },
    #             "ipcomp": "true",
    #             "enabled": "1",
    #             "dpdaction": "none",
    #             "keyexchange": self.ike_version,
    #             "remote_subnet": ["192.168.50.0/24"],
    #             "local_subnet": ["192.168.150.0/24"],
    #             "gateway": "192.168.2.194",
    #             "local_identifier": self.local_identifier,
    #             "remote_identifier": self.remote_identifier,
    #             "local_ip": spoke_ip,
    #             "pre_shared_key": "qL7UKwQl4HbYzmZwT0Eyzu4txAPZ3avgiV8yGRsh35LO9d81MhDVV0AqHNs51Tbr0HNxrb/gahhnOW17Avf6aB0V"
    #         }
     
    #         # hub_push = push_ipsec_config_by_mgmt_ip(hub_ip, hub_payload)
    #         # spoke_push = push_ipsec_config_by_mgmt_ip(spoke_ip, spoke_payload)
            
    #         # TunnelStatusLog.objects.create(
    #         #     tunnel=self,
    #         #     status=hub_push.get('status') == 'success' and spoke_push.get('status') == 'success'
    #         #            and 'success' or 'error',
    #         #     log=(
    #         #         f"Site-to-Site IPSec push for {spoke.name}: "
    #         #         f"Hub status={hub_push.get('status')} ({hub_push.get('message', '')}), "
    #         #         f"Spoke status={spoke_push.get('status')} ({spoke_push.get('message', '')})"
    #         #     )
    #         # )
    #         # results.append({
    #         # "device": spoke.name,
    #         # "hub_result": hub_push,
    #         # "spoke_result": spoke_push,
    #         # })

    #         # return results

    #         # Step 5: Push set-config to device_a (Hub) with device_b info
    #         hub_result = push_ipsec_config_by_mgmt_ip(hub_ip, hub_payload)
           
    #         # Step 6: Push set-config to device_b (Spoke) with device_a info
    #         spoke_result = push_ipsec_config_by_mgmt_ip(spoke_ip, spoke_payload)
     
    #         # Log results and push status update
    #         if hub_result.get("status") != "error" and spoke_result.get("status") != "error":
    #             self.status = 'active'
    #             self.last_pushed_at = timezone.now()
    #         else:
    #             self.status = 'error'
     
    #         self.save()
     
    #         TunnelStatusLog.objects.create(
    #             tunnel=self,
    #             status=self.status,
    #             log=f"Site-to-Site IPSec push for {spoke.name}: Hub: {hub_result.get('status')}, Spoke: {spoke_result.get('status')}"
    #         )
     
    #         results.append({
    #             "device": spoke.name,
    #             "hub_result": hub_result,
    #             "spoke_result": spoke_result
    #         })
     
    #     return results
   

    def rollback_last_config(self):
        last = self.config_history.order_by('-generated_at').first()
        if last:
            agent_url = self.get_agent_url()
            if agent_url:
                try:
                    response = requests.post(agent_url, json={'config': last.config_snapshot}, timeout=10)
                    response.raise_for_status()
                    return {"status": "success", "message": f"Rollback successful for {self.name}"}
                except Exception as e:
                    return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "No rollback config available."}
   
    def push_to_agent(self, max_retries=3, delay=2):
        try:
            if self.vpn_type == "ipsec" and self.mode == "site_to_site":
                
                results = self.push_site_to_site_ipsec_config()
                # return{"status": "success", "message": "push_site_to_site_ipsec_config implemented"}
                # Fix: Ensure results is a list
                if not isinstance(results, list):
                    # Convert dict to list of dicts if needed
                    if isinstance(results, dict):
                        results = [results]
                    else:
                        raise TypeError("push_site_to_site_ipsec_config must return a list of result dicts")
      
                # Check for any errors in the results
                error_devices = [r for r in results if isinstance(r, dict) and (r.get("hub_result", {}).get("status") == "error" or r.get("spoke_result", {}).get("status") == "error")]
                if error_devices:
                    self.status = 'error'
                    self.save()
                    TunnelStatusLog.objects.create(
                        tunnel=self,
                        status='failed',
                        log=f"Push failed for devices: {', '.join([r['device'] for r in error_devices])}"
                    )
                    return {
                        "status": "error",
                        "message": f"Push failed for some devices: {', '.join([r['device'] for r in error_devices])}",
                        "details": results
                    }
      
                # All success: record config push
                config_string = str(results)  # Simplified: use actual config string if needed
                config_hash = hashlib.sha256(config_string.encode()).hexdigest()
                
                # if config_hash == self.last_config_hash:
                #     return {
                #         "status": "skipped",
                #         "message": f"Tunnel '{self.name}' config is already up to date. Push skipped."
                #     }
      
                self.last_pushed_at = timezone.now()
                self.last_config_hash = config_hash
                self.status = 'active'
                self.save()
      
                TunnelConfigHistory.objects.create(
                    tunnel=self,
                    config_snapshot=self.export_json(),
                    config_text=config_string,
                    triggered_by=getattr(self, 'created_by', None)
                )
                TunnelStatusLog.objects.create(
                    tunnel=self,
                    status='success',
                    log='Pushed via centralized config API'
                )
      
                return {
                    "status": "success",
                    "message": f"Tunnel '{self.name}' pushed successfully.",
                    "details": results
                }
      
            else:
                return {
                    "status": "skipped",
                    "message": "Unsupported VPN type or mode for push operation."
                }
      
        except Exception as e:
            self.status = 'error'
            self.save()
            TunnelStatusLog.objects.create(
                tunnel=self,
                status='failed',
                log=str(e),
                retry_count=1
            )
            # mail_admins(
            #     "Tunnel Push Failed",
            #     f"Tunnel '{self.name}' failed to push.\nError: {str(e)}"
            # )
            # return {
            #     "status": "error",
            #     "message": f"Tunnel '{self.name}' push failed: {str(e)}"
            # }
            # try:
            #     mail_admins(
            #         "Tunnel Push Failed",
            #         f"Tunnel '{self.name}' failed to push.\nError: {e}"
            #     )
            # except Exception as email_err:
            #     logging.error(f"Failed to send admin email: {email_err}")
            return {"status": "error", "message": f"Tunnel '{self.name}' push failed: {e}"} 



    def auto_push_on_create(sender, instance, created, **kwargs):
        if created and instance.is_active:
            try:
                if not instance.device_peers.filter(local_role='hub').exists():
                    raise ValueError("No DevicePeer with role 'hub' found. Skipping push.")
                result = instance.push_to_agent()
                TunnelStatusLog.objects.create(tunnel=instance, status=result['status'], log=result['message'])
            except Exception as e:
                TunnelStatusLog.objects.create(
                    tunnel=instance,
                    status='failed',
                    log=f'Auto-push error: {str(e)}'
            )




class TunnelStatusLog(models.Model):
    tunnel = models.ForeignKey(Tunnel, on_delete=models.CASCADE)
    status = models.CharField(max_length=64)
    log = models.TextField()
    retry_count = models.PositiveIntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tunnel.name} - {self.status} @ {self.timestamp}"

class TunnelHealthMetric(models.Model):
    tunnel = models.ForeignKey(Tunnel, on_delete=models.CASCADE, related_name='health_metrics')
    latency_ms = models.FloatField()
    jitter_ms = models.FloatField()
    packet_loss_percent = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Health: {self.tunnel.name} @ {self.timestamp}"

class TunnelConfigHistory(models.Model):
    tunnel = models.ForeignKey(Tunnel, on_delete=models.CASCADE, related_name='config_history')
    config_snapshot = models.TextField()
    config_text = models.TextField(null=True, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    triggered_by = models.ForeignKey(OrganizationUser, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"History: {self.tunnel.name} @ {self.generated_at}"

class DevicePeer(models.Model):
    ROLE_CHOICES = [
        ('hub', 'Hub'),
        ('spoke', 'Spoke')
    ]
    organization = models.ForeignKey('openwisp_users.Organization', on_delete=models.CASCADE)
    tunnel = models.ForeignKey(Tunnel, on_delete=models.CASCADE, related_name='device_peers')
    local_device_name = models.CharField(max_length=128)
    local_ip = models.GenericIPAddressField()
    peer_device_name = models.CharField(max_length=128)
    peer_ip = models.GenericIPAddressField()
    link_subnet = models.CharField(max_length=64)
    local_role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    peer_role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('tunnel', 'local_device_name', 'peer_device_name')

    def __str__(self):
        return f"{self.local_device_name} <-> {self.peer_device_name} ({self.tunnel.name})"


class TunnelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tunnel
        fields = '__all__'

    def validate_spoke_lan_subnet(self, value):
        if not value:
            return value
        from ipaddress import ip_network
        try:
            subnet = ip_network(value)
            if subnet.prefixlen < 24 or subnet.prefixlen > 30:
                raise serializers.ValidationError("Subnet prefix must be between /24 and /30.")
        except ValueError:
            raise serializers.ValidationError("Invalid CIDR format.")
        if Tunnel.objects.filter(spoke_lan_subnet=value).exists():
            raise serializers.ValidationError("This subnet is already in use.")
        return value

