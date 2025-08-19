import logging
from celery import shared_task
import hashlib ,requests
from django.utils import timezone
import json

import secrets
import string
from django.core.exceptions import ObjectDoesNotExist
from sdwan_tunnel.protocols.ipsec.client import (fetch_online_devices_by_names,
    fetch_management_ips_by_names,
    push_ipsec_config_by_mgmt_ip ,
    get_ipsec_config_by_mgmt_ip ,
    get_ip_config_by_mgmt_ip)

logger = logging.getLogger(__name__)




@shared_task
def push_hub_spoke_tunnel_async(spoke_id ,job_id):
    from sdwan_tunnel.models import Spoke , Job
    job = Job.objects.get(pk=job_id)
    """
    1) Fetch management IPs for hub and spoke
    2) Check if ipsec_server config exists on hub
    3) Verify both devices online
    4) Generate PSK on hub if missing
    5) Assign WAN IPs if missing
    6) Build and push configuration payload to both hub and spoke
    """
    try:
        spoke = Spoke.objects.get(pk=spoke_id)
        hub = spoke.hub_device

        # 1) Get management IPs
        device_names = [hub.local_device.name, spoke.device.name]
        mgmt_map = fetch_management_ips_by_names(device_names)
        # hub_ip = mgmt_map.get(hub.local_device.name)
        # spoke_ip = mgmt_map.get(spoke.device.name)
        hub_info      = mgmt_map.get(hub.local_device.name, {})
        hub_ip        = hub_info.get("management_ip")
        hub_last_ip   = hub_info.get("last_ip")
        spoke_info      = mgmt_map.get(spoke.device.name, {})
        spoke_ip        = spoke_info.get("management_ip")
        spoke_last_ip   = spoke_info.get("last_ip")
        
        hub.local_ip = hub_ip
        spoke.local_ip =spoke_ip
        hub.save(update_fields=["local_ip"])
        spoke.save(update_fields=["local_ip"])

        def generate_psk(hub=None, length: int = 9) -> str:
            """
            Generate a pre-shared key of the form:
              nexapp<digits>
            e.g. “nexapp123456789”
            """
            # choose only digits for the “xxxxxxxxx” part
            digits = ''.join(secrets.choice(string.digits) for _ in range(length))
            return f'nexapp{digits}'

     
        # 2a) Fetch the list of existing tunnels on the spoke
        existingTunnelId = None
        tunnelexist = False
        target=f'{hub.name}'
        if spoke_ip:
            config_url = f"https://{spoke_ip}/api-new/ipsec"
            try:
                resp = requests.post(config_url, json={"method":"get-config","payload":{}}, 
                     verify=False, timeout=15)
           
                resp.raise_for_status()
                data = resp.json().get("data", {})
                tunnels = data.get("tunnels", [])
               
                # 4) Now extract the one that matches hub.name exactly
                matching_ids = [t["id"] for t in tunnels if t.get("name") == target]
                if matching_ids:
                    existingTunnelId = matching_ids[0]
                    tunnelexist=True
                else:
                    existingTunnelId = None
                    tunnelexist=False
                print(existingTunnelId)
                
            except Exception as e:
                logger.error(f"[push] error fetching existing tunnels from {spoke_ip}: {e}")  
        
        hubtunnel_id=None
        hubtunnelexist=False
        existing_remotes =[]
        if hub_ip:
            config_url = f"https://{hub_ip}/api-new/ipsec"
            try:
                resp = requests.post(config_url, json={"method":"get-config","payload":{}}, 
                     verify=False, timeout=15)
           
                resp.raise_for_status()
                data = resp.json().get("data", {})
                tunnels = data.get("tunnels", [])
               
                if not tunnels:
                    # no tunnel present → start with empty remote list
                    hubtunnel_id     = None
                    existing_remotes = []
                else:
                    tunnel           = tunnels[0]
                    hubtunnel_id        = tunnel.get("id")
                    existing_remotes = tunnel.get("remote", [])
                    hubtunnelexist=True
                # 3) Only append spoke.subnet if it's not already in the list
                if spoke.subnet not in existing_remotes:
                    existing_remotes.append(spoke.subnet)
                print(hubtunnel_id,existing_remotes)
                
            except Exception as e:
                logger.error(f"[push] error fetching existing tunnels from {hub_ip}: {e}")  
        

        
        # 3) Verify both devices online
        online = fetch_online_devices_by_names(device_names)
        if len(online) != len(device_names):
            
            msg = f"Not all devices are online: {device_names}"
            logger.error(f"[push] {msg}")
        
            job.status = 'failure'
            job.message = msg
            job.finished_at = timezone.now()
            job.save()
        
            spoke.last_push_message = msg
            spoke.last_pushed_at = timezone.now()
            spoke.save(update_fields=["last_push_message", "last_pushed_at"])
        
            return {"status": "error", "message": msg}
       
        if not hub_ip and not spoke_ip :
            msg = f"Not all devices are online: {device_names}"
            logger.error(f"[push] {msg}")
        
            job.status = 'failure'
            job.message = msg
            job.finished_at = timezone.now()
            job.save()
        
            spoke.last_push_message = msg
            spoke.last_pushed_at = timezone.now()
            spoke.save(update_fields=["last_push_message", "last_pushed_at"])
        
            return {"status": "error", "message": msg}
        
        if not spoke_ip:
            msg = f"device are not online: {spoke.device.name}"
            logger.error(f"[push] {msg}")
            job.status = 'failure'
            job.message = msg
            job.finished_at = timezone.now()
            job.save()
            spoke.last_push_message = msg
            spoke.last_pushed_at = timezone.now()
            spoke.save(update_fields=["last_push_message", "last_pushed_at"])
            return {"status": "error", "message": msg}
        
        if not hub_ip:
            msg = f"device are not online: {hub.device.name}"
            logger.error(f"[push] {msg}")
            job.status = 'failure'
            job.message = msg
            job.finished_at = timezone.now()
            job.save()
            spoke.last_push_message = msg
            spoke.last_pushed_at = timezone.now()
            spoke.save(update_fields=["last_push_message", "last_pushed_at"])
            return {"status": "error", "message": msg}


        # 5) Assign WAN IP on hub
        if not hub.wan_ip and hub_ip:
            info = get_ip_config_by_mgmt_ip(hub_ip)
            wan_list = info.get("data", {}).get("local_wan_ip", [])
            if wan_list:
                wan_ip = wan_list[0]["ip"]
            else:
                wan_ip = None
            
            if wan_ip:
                hub.wan_ip = wan_ip
                hub.save(update_fields=["wan_ip"])

        # Ensure spoke WAN IP as well
        if not spoke.wan_ip and spoke_ip:
            info2 = get_ip_config_by_mgmt_ip(spoke_ip)
            # wan2_list = info2.get("data", {}).get("local_wan_ip", [])
            # if wan2_list:
            #     wan2 = wan2_list[0]["ip"]
            # else:
            #     wan2 = None
            # if wan2:
            #     spoke.wan_ip = wan2
            #     spoke.save(update_fields=["wan_ip"])


            data = info2.get('data', {}) or {}
            local = data.get("local_wan_ip")

            if isinstance(local, list):
                spoke.wan_ip = local[0].get("ip")
            elif isinstance(local, str):
                spoke.wan_ip = local
            elif isinstance(local, dict):
                spoke.wan_ip = local.get("ip")
            else:
                spoke.wan_ip = None
            
            if local:
                spoke.save(update_fields=["wan_ip"])
                logger.info(f"Set spoke {spoke.pk} WAN IP to {spoke.wan_ip}")
            else:
                logger.warning(f"No valid WAN IP found in response: {info2}")

        # 6) Build payload for hub
       
        if not hub.pre_shared_key:
            hub.pre_shared_key = generate_psk(hub)
            hub.save(update_fields=["pre_shared_key"])
         
        hub_push=False
        spoke_push=False


        if hub_ip:
            hub_url = f"https://{hub_ip}/api-new/ipsec"
            if hubtunnelexist:
                hubmethod = "edit-tunnel"
                logger.debug(f"[push] hub {hub.pk}: editing tunnel {hubtunnel_id}")
            else:
                hubmethod = "add-tunnel"
                logger.debug(f"[push] hub {spoke.pk}: adding new tunnel '{hub.name}'")
            
            hubcfg={
                    "ns_name": hub.name,
                    "enabled": "1" if spoke.is_enabled else "0",
                    "dpdaction": hub.dpdaction,
                    "ipcomp": "true" if hub.ipcomp else "false",

                    "keyexchange": hub.ike_version,
                    "pre_shared_key": hub.pre_shared_key,
                    "remote_subnet": existing_remotes,
                    "local_subnet": [hub.subnet], 
                    "local_identifier":hub_last_ip,
                    "remote_identifier": "%any",
                    "gateway":  'any', 
                    "local_ip": hub.wan_ip ,
                    
                    "ike": {
                        "hash_algorithm": hub.ike_integrity_algorithm,
                        "encryption_algorithm": hub.ike_encryption_algorithm,
                        "dh_group": hub.ike_diffie_hellman_group,
                        "rekeytime": str(hub.ike_key_lifetime),
                    },
                    "esp": {
                        "hash_algorithm": hub.esp_integrity_algorithm,
                        "encryption_algorithm": hub.esp_encryption_algorithm,
                        "dh_group": hub.esp_diffie_hellman_group,
                        "rekeytime": str(hub.esp_key_lifetime),
                    },
            }
            if hubtunnelexist:
                hubcfg["id"] = hubtunnel_id

            hub_payload = {
                "method": hubmethod,
                "payload": hubcfg
                
            }
        # Push config to hub
            try:
    
                resp1 = requests.post(
                    hub_url,
                    json=hub_payload,
                    verify=False,
                    timeout=15
                )
                resp1.raise_for_status()
                hub_push =True
                hub.last_pushed_at = timezone.now()
                hub.save(update_fields=["last_pushed_at"])
                logger.info(f"[push] edit-config response for hub {hub.pk}: {resp1.text}")
            except Exception as e:
                logger.error(f"[push] failed to edit-config on hub {hub.pk}: {e}")
       
        # 7) Build payload for spoke and push
       
        if spoke_ip:
            spoke_url = f"https://{spoke_ip}/api-new/ipsec"
            if tunnelexist:
                method = "edit-tunnel"
                logger.debug(f"[push] spoke {spoke.pk}: editing tunnel {existingTunnelId}")
            else:
                method = "add-tunnel"
                logger.debug(f"[push] spoke {spoke.pk}: adding new tunnel '{hub.name}'")
            
            cfg={
                    "ns_name": hub.name,
                    "enabled": "1" if spoke.is_enabled else "0",
                    "dpdaction": hub.dpdaction,
                    "ipcomp": "true" if hub.ipcomp else "false",

                    "keyexchange": hub.ike_version,
                    "pre_shared_key": hub.pre_shared_key,
                    "remote_subnet": [hub.subnet],
                    "local_subnet": [spoke.subnet], 
                    "local_identifier": spoke_last_ip,
                    "remote_identifier": hub_last_ip,
                    "gateway": hub_last_ip, 
                    "local_ip": spoke.wan_ip,
                    
                    "ike": {
                        "hash_algorithm": hub.ike_integrity_algorithm,
                        "encryption_algorithm": hub.ike_encryption_algorithm,
                        "dh_group": hub.ike_diffie_hellman_group,
                        "rekeytime": str(hub.ike_key_lifetime),
                    },
                    "esp": {
                        "hash_algorithm": hub.esp_integrity_algorithm,
                        "encryption_algorithm": hub.esp_encryption_algorithm,
                        "dh_group": hub.esp_diffie_hellman_group,
                        "rekeytime": str(hub.esp_key_lifetime),
                    },
            }
            if tunnelexist:
                cfg["id"] = existingTunnelId
            
            spoke_payload = {
                "method": method,
                "payload": cfg
                }

            try:
                resp3 = requests.post(
                    spoke_url,
                    json=spoke_payload,
                    verify=False,
                    timeout=15
                )
                resp3.raise_for_status()
                spoke_push=True
                spoke.last_pushed_at    = timezone.now()

                spoke.save(update_fields=["last_pushed_at"])
                logger.info(f"[push] set-config response for spoke {spoke.pk}: {resp3.text}")
            except Exception as e:
                logger.error(f"[push] failed to push config to spoke {spoke.pk}: {e}")


        if hub_push and spoke_push:
            
            job.status = 'success'
            job.message = "Tunnel push completed successfully"
            job.finished_at = timezone.now()
            job.save()
            spoke.last_push_message = "Tunnel push completed successfully"
            spoke.last_pushed_at = timezone.now()
            spoke.save(update_fields=["last_push_message", "last_pushed_at"])
            return {"status": "pushed", "message": "Config pushed to both devices",
                    "hub_payload": hub_payload, "spoke_payload": spoke_payload}
        
        if spoke_push and not hub_push :
            job.status = 'error'
            job.message = "configuration not pushed in hub device"
            job.finished_at = timezone.now()
            job.save()
            spoke.last_push_message = "configuration not pushed in Hub device"
            spoke.last_pushed_at = timezone.now()
            spoke.save(update_fields=["last_push_message", "last_pushed_at"])

            return {"status": "pushed", "message": " configuration not pushed in Hub device",
                        "spoke_payload": spoke_payload}
        if hub_push and not spoke_push :
            job.status = 'error'
            job.message = "configuration not pushed in Spoke device"
            job.finished_at = timezone.now()
            job.save()
            spoke.last_push_message = "configuration not pushed in Spoke device"
            spoke.last_pushed_at = timezone.now()
            spoke.save(update_fields=["last_push_message", "last_pushed_at"])

            return {"status": "pushed", "message": "configuration not pushed in Spoke device",
                        "hub_payload": hub_payload}
        

        

    except ObjectDoesNotExist:
        msg = f"Spoke {spoke_id} not found"
        logger.error(f"[push] {msg}")
        job.status = 'failure'
        job.message = msg
        job.finished_at = timezone.now()
        job.save()
        spoke.last_push_message = f"Push failed: {msg}"
        spoke.last_pushed_at = timezone.now()
        spoke.save(update_fields=["last_push_message", "last_pushed_at"])
        return {"status": "error", "message": msg}
    except Exception as exc:
        logger.exception(f"[push] unexpected error for spoke {spoke_id}: {exc}")
        job.status = 'failure'
        job.message = f"Failed: {exc}"
        job.finished_at = timezone.now()
        job.save()
        spoke.last_push_message = f"Push failed: {exc}"
        spoke.last_pushed_at = timezone.now()
        spoke.save(update_fields=["last_push_message", "last_pushed_at"])
        raise
        # return {"status": "error", "message": str(exc)}


  
