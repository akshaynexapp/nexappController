# sdwan_tunnel/protocols/ipsec/handlers/site_to_site.py
"""
Site-to-Site IPsec Handler (Phase 1)
Coordinates:
 1. PSK generation (persisted)
 2. Subnet allocation (persisted)
 3. Render config via Jinja2 template
 4. Push config to both endpoints via API
 5. Record history and status, with real hash
 6. Support rollback to previous config snapshot
"""
import os
import logging

import hashlib ,requests
from django.core.exceptions import ObjectDoesNotExist

from django.utils import timezone
from sdwan_tunnel.tasks.helpers import get_ipsec_payloads
from jinja2 import Environment, FileSystemLoader
from sdwan_tunnel.services.key_manager import generate_psk
from sdwan_tunnel.services.subnet_allocate import allocate_subnet
from sdwan_tunnel.services.config_fetch import fetch_config
from sdwan_tunnel.services.config_modify import render_config
from sdwan_tunnel.services.config_push import push_config
from sdwan_tunnel.utils.logging_utils import structured_log
from sdwan_tunnel.protocols.ipsec.client import (
    
    fetch_online_devices_by_names,
    fetch_management_ips_by_names,
    push_ipsec_config_by_mgmt_ip ,
    get_ipsec_config_by_mgmt_ip ,
    get_ip_config_by_mgmt_ip
)
# Locate templates directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'protocols', 'ipsec', 'templates')
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=False)

logger = logging.getLogger(__name__)
def deploy_site_to_site(tunnel_id,job_id, full_replace=False):
    # Deferred imports to break circular dependencies
    from sdwan_tunnel.models.tunnel import Tunnel
    from sdwan_tunnel.models import Job
    from sdwan_tunnel.models.config_history import ConfigHistory

    try: 
        tunnel = Tunnel.objects.get(id=tunnel_id)
        job = Job.objects.get(pk=job_id)

    
        
        # 2) Validate devices online
    
        device_names = [tunnel.device_a.name] + [tunnel.device_b.name]
        print(">>> Device names:", device_names)
        online = fetch_online_devices_by_names(device_names)
        if len(online) != len(device_names):
             
            msg = f"Not all devices are online: {device_names}"
            logger.error(f"[push] {msg}")
        
            job.status = 'failure'
            job.message = msg
            job.finished_at = timezone.now()
            job.save()
        
            tunnel.last_push_message = msg
            tunnel.last_pushed_at = timezone.now()
            tunnel.save(update_fields=["last_push_message", "last_pushed_at"])
        
            return {"status": "error", "message": msg}
        
    
        # 3) Discover management IPs
        mgmt_map = fetch_management_ips_by_names(device_names)
        device_a_info      = mgmt_map.get(tunnel.device_a.name, {})
        device_a_ip        = device_a_info.get("management_ip")
        device_a_last_ip   = device_a_info.get("last_ip")
        device_b_info      = mgmt_map.get(tunnel.device_b.name, {})
        device_b_ip        = device_b_info.get("management_ip")
        device_b_last_ip   = device_b_info.get("last_ip")
        
        tunnel.local_ip_a = device_a_ip
        tunnel.local_ip_b =device_b_ip
        tunnel.save(update_fields=["local_ip_b",'local_ip_a'])
    
        existingTunnel_a_Id = None
        tunnel_a_exist = False
        target=f'{tunnel.name}'
        if device_a_ip:
            config_url = f"https://{device_a_ip}/api-new/ipsec"
            try:
                resp = requests.post(config_url, json={"method":"get-config","payload":{}}, 
                     verify=False, timeout=15)
           
                resp.raise_for_status()
                data = resp.json().get("data", {})
                tunnels = data.get("tunnels", [])
               
                # 4) Now extract the one that matches hub.name exactly
                matching_ids = [t["id"] for t in tunnels if t.get("name") == target]
                if matching_ids:
                    existingTunnel_a_Id = matching_ids[0]
                    tunnel_a_exist=True
                else:
                    existingTunnel_a_Id = None
                    tunnel_a_exist=False
                print(existingTunnel_a_Id)
                
            except Exception as e:
                logger.error(f"[push] error fetching existing tunnels from {device_a_ip}: {e}")
    
        existingTunnel_b_Id = None
        tunnel_b_exist = False
        target=f'{tunnel.name}'

        if device_b_ip:
            config_url = f"https://{device_b_ip}/api-new/ipsec"
            try:
                resp = requests.post(config_url, json={"method":"get-config","payload":{}}, 
                     verify=False, timeout=15)
           
                resp.raise_for_status()
                data = resp.json().get("data", {})
                tunnels = data.get("tunnels", [])
               
                # 4) Now extract the one that matches hub.name exactly
                matching_ids = [t["id"] for t in tunnels if t.get("name") == target]
                if matching_ids:
                    existingTunnel_b_Id = matching_ids[0]
                    tunnel_b_exist=True
                else:
                    existingTunnel_b_Id = None
                    tunnel_b_exist=False
                print(existingTunnel_a_Id)
                
            except Exception as e:
                logger.error(f"[push] error fetching existing tunnels from {device_b_ip}: {e}")
    
        if any(name not in mgmt_map for name in device_names):
            return {"status": "error", "message": "Failed to fetch management IPs"}
        print(">>> mgmt_map:", mgmt_map)
    
        # 4) PSK generation
        if not tunnel.pre_shared_key:
            tunnel.pre_shared_key = generate_psk(tunnel)
     
       
        # 6-8) Render, push, record
        last_hash = None
        device_wan_ip=None
        tunnel.save(update_fields=['pre_shared_key'])
        mgmt_ip_a = device_a_ip
        if not tunnel.device_a_wan_ip:
            device_a_ip_network = get_ip_config_by_mgmt_ip(mgmt_ip_a)
            wan_list = device_a_ip_network.get("data", {}).get("local_wan_ip", [])
            if wan_list:
                device_wan_ip = wan_list[0]["ip"]
            else:
                device_wan_ip = None
            
        if device_wan_ip:
            tunnel.device_a_wan_ip = device_wan_ip
            tunnel.save(update_fields=['device_a_wan_ip'])
    
    
        mgmt_ip_b = device_b_ip
        device_wan_ip_b =None
        print(">>> mgmt_ip_b:", mgmt_ip_b)
        if not tunnel.device_b_wan_ip:
            device_b_ip_network= get_ip_config_by_mgmt_ip(mgmt_ip_b)
            
            wan_list_b = device_b_ip_network.get("data", {}).get("local_wan_ip", [])
            if wan_list_b:
                device_wan_ip_b = wan_list_b[0]["ip"]
            else:
                device_wan_ip_b = None
        
        if device_wan_ip_b:
            tunnel.device_b_wan_ip = device_wan_ip_b
            tunnel.save(update_fields=['device_b_wan_ip'])
    
        device_a_push =False
        device_b_push =False
    
        if device_a_ip:
            device_a_url = f"https://{device_a_ip}/api-new/ipsec"
            if tunnel_a_exist:
                method = "edit-tunnel"
                logger.debug(f"[push] tunnel {tunnel.pk}: editing tunnel {existingTunnel_a_Id}")
            else:
                method = "add-tunnel"
                logger.debug(f"[push] tunnel {tunnel.pk}: adding new tunnel '{tunnel.name}'")
            
            cfg={
                    "ns_name": tunnel.name,
                    "enabled": "1" if tunnel.is_enabled else "0",
                    "dpdaction": tunnel.dpdaction,
                    "ipcomp": "true" if tunnel.ipcomp else "false",

                    "keyexchange": tunnel.ike_version,
                    "pre_shared_key": tunnel.pre_shared_key,
                    "remote_subnet": [tunnel.device_b_subnet],
                    "local_subnet": [tunnel.device_a_subnet], 
                    "local_identifier": device_a_last_ip,
                    "remote_identifier": device_b_last_ip,
                    "gateway": device_b_last_ip, 
                    "local_ip": tunnel.device_a_wan_ip,
                    
                    "ike": {
                        "hash_algorithm": tunnel.ike_integrity_algorithm,
                        "encryption_algorithm": tunnel.ike_encryption_algorithm,
                        "dh_group": tunnel.ike_diffie_hellman_group,
                        "rekeytime": str(tunnel.ike_key_lifetime),
                    },
                    "esp": {
                        "hash_algorithm": tunnel.esp_integrity_algorithm,
                        "encryption_algorithm": tunnel.esp_encryption_algorithm,
                        "dh_group": tunnel.esp_diffie_hellman_group,
                        "rekeytime": str(tunnel.esp_key_lifetime),
                    },
            }
           
            if tunnel_a_exist:
                cfg["id"] = existingTunnel_a_Id
             
            device_a_payload = {
                "method": method,
                "payload": cfg
                }

            try:
                resp3 = requests.post(
                    device_a_url,
                    json=device_a_payload,
                    verify=False,
                    timeout=15
                )
                resp3.raise_for_status()
                tunnel.last_pushed_at    = timezone.now()
                device_a_push=True
                tunnel.save(update_fields=["last_pushed_at"])
                logger.info(f"[push] set-config response for spoke {tunnel.pk}: {resp3.text}")
            except Exception as e:
                logger.error(f"[push] failed to push config to spoke {tunnel.pk}: {e}")
    
          
        if device_b_ip:
            device_b_url = f"https://{device_b_ip}/api-new/ipsec"
            if tunnel_b_exist:
                device_b_method = "edit-tunnel"
                logger.debug(f"[push] tunnel {tunnel.pk}: editing tunnel {existingTunnel_b_Id}")
            else:
                device_b_method = "add-tunnel"
                logger.debug(f"[push] tunnel {tunnel.pk}: adding new tunnel '{tunnel.name}'")
            
            device_b_cfg={
                    "ns_name": tunnel.name,
                    "enabled": "1" if tunnel.is_enabled else "0",
                    "dpdaction": tunnel.dpdaction,
                    "ipcomp": "true" if tunnel.ipcomp else "false",

                    "keyexchange": tunnel.ike_version,
                    "pre_shared_key": tunnel.pre_shared_key,
                    "remote_subnet": [tunnel.device_a_subnet],
                    "local_subnet": [tunnel.device_b_subnet], 
                    "local_identifier":device_b_last_ip,
                    "remote_identifier": device_a_last_ip,
                    "gateway":  device_a_last_ip, 
                    "local_ip": tunnel.device_b_wan_ip ,
                    
                    "ike": {
                        "hash_algorithm": tunnel.ike_integrity_algorithm,
                        "encryption_algorithm": tunnel.ike_encryption_algorithm,
                        "dh_group": tunnel.ike_diffie_hellman_group,
                        "rekeytime": str(tunnel.ike_key_lifetime),
                    },
                    "esp": {
                        "hash_algorithm": tunnel.esp_integrity_algorithm,
                        "encryption_algorithm": tunnel.esp_encryption_algorithm,
                        "dh_group": tunnel.esp_diffie_hellman_group,
                        "rekeytime": str(tunnel.esp_key_lifetime),
                    },
            }
            
            if tunnel_b_exist:
                device_b_cfg["id"] = existingTunnel_b_Id
            


            hub_payload = {
                "method": device_b_method,
                "payload": device_b_cfg
                
                
            }
        # Push config to hub
            try:
    
                resp1 = requests.post(
                    device_b_url,
                    json=hub_payload,
                    verify=False,
                    timeout=15
                )
                resp1.raise_for_status()
                tunnel.last_pushed_at = timezone.now()
                device_b_push=True

                tunnel.save(update_fields=["last_pushed_at"])
                logger.info(f"[push] edit-config response for hub {tunnel.pk}: {resp1.text}")
            except Exception as e:
                logger.error(f"[push] failed to edit-config on hub {tunnel.pk}: {e}")
           
        if device_a_push and device_b_push:
            job.status = 'success'
            job.message = "Tunnel push completed successfully"
            job.finished_at = timezone.now()
            job.save()
            tunnel.last_push_message = "Tunnel push completed successfully"
            tunnel.last_pushed_at = timezone.now()
            tunnel.save(update_fields=["last_push_message", "last_pushed_at"])
               
            return {"status": "pushed", "message": "Config pushed to both devices",
                        "hub_payload": hub_payload, "spoke_payload": device_a_payload}
        
        elif device_b_push and not device_a_push :
            job.status = 'error'
            job.message = "Device b is not reachable"
            job.finished_at = timezone.now()
            job.save()
            tunnel.last_push_message = "Failed to push config in Device A"
            tunnel.last_pushed_at = timezone.now()
            tunnel.save(update_fields=["last_push_message", "last_pushed_at"])
            return {"status": "pushed", "message": "Config pushed to  device a",
                        "device_b_payload": hub_payload}
        elif device_a_push and not device_b_push :
            job.status = 'error'
            job.message = "Device a is not reachable"
            job.finished_at = timezone.now()
            job.save()
            tunnel.last_push_message = "Tunnel push in Device a only Device b is not reachable"
            tunnel.last_pushed_at = timezone.now()
            tunnel.save(update_fields=["last_push_message", "last_pushed_at"])
            return {"status": "pushed", "message": "Config pushed to  device b",
                        "device_a_payload": device_a_payload}
        else:
            return {"status": "error", "message": "Failed pushed, Device not reachable",
                        }


    except ObjectDoesNotExist:
        msg = f"tunnel {tunnel_id} not found"
        logger.error(f"[push] {msg}")
        job.status = 'failure'
        job.message = msg
        job.finished_at = timezone.now()
        job.save()
        tunnel.last_push_message = f"Push failed: {msg}"
        tunnel.last_pushed_at = timezone.now()
        tunnel.save(update_fields=["last_push_message", "last_pushed_at"])
        return {"status": "error", "message": msg}
    except Exception as exc:
        logger.exception(f"[push] unexpected error for tunnel {tunnel_id}: {exc}")
        job.status = 'failure'
        job.message = f"Failed: {exc}"
        job.finished_at = timezone.now()
        job.save()
        tunnel.last_push_message = f"Push failed: {exc}"
        tunnel.last_pushed_at = timezone.now()
        tunnel.save(update_fields=["last_push_message", "last_pushed_at"])
        raise
   
 
   
    

def rollback_site_to_site(tunnel_id, full_replace=False):
    from sdwan_tunnel.models.tunnel import Tunnel
    from sdwan_tunnel.models.config_history import ConfigHistory
    from sdwan_tunnel.models.tunnel_status import TunnelStatus
 
    tunnel = Tunnel.objects.get(id=tunnel_id)
    """
    Restores the most recent ConfigHistory entry for a tunnel.
    """
    try:
        tunnel = Tunnel.objects.get(id=tunnel_id)
    except Tunnel.DoesNotExist:
        return {'status': 'error', 'message': 'Tunnel not found'}

    last_entry = (
        ConfigHistory.objects
        .filter(tunnel=tunnel)
        .order_by('-created_at')
        .first()
    )
    if not last_entry:
        return {'status': 'error', 'message': 'No rollback config available'}

    # Archive the rollback action itself
    ConfigHistory.objects.create(
        tunnel=tunnel,
        config_hash=last_entry.config_hash,
        payload=last_entry.payload,
        action='rollback'
    )

    # Re-apply saved payload
    errors = []
    for call in last_entry.payload:
        host = call['payload']['local_ip']
        url = f"https://{host}/api-new/ipsec"
        try:
            resp = requests.post(url, json=call, verify=False, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            errors.append(f"{host}: {e}")

    if errors:
        return {'status': 'error', 'message': '; '.join(errors)}

    tunnel.status = 'rolled_back'
    tunnel.last_pushed_at = timezone.now()
    tunnel.save()
    return {'status': 'success', 'message': 'Rollback applied successfully'}
