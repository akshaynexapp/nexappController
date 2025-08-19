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
import hashlib ,requests
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


def deploy_site_to_site(tunnel_id, full_replace=False):
    # Deferred imports to break circular dependencies
    from sdwan_tunnel.models.tunnel import Tunnel
    from sdwan_tunnel.models.config_history import ConfigHistory
    from sdwan_tunnel.models.tunnel_status import TunnelStatus
 
    tunnel = Tunnel.objects.get(id=tunnel_id)

    
    # 2) Validate devices online
  






    device_names = [tunnel.device_a.name] + [tunnel.device_b.name]
    print(">>> Device names:", device_names)
    online = fetch_online_devices_by_names(device_names)
    if len(online) != len(device_names):
        print(">>> erro online devices:", online)
        return {"status": "error", "message": "Not all devices are online"}
    

    # 3) Discover management IPs
    mgmt_map = fetch_management_ips_by_names(device_names)
    device_a_info      = mgmt_map.get(tunnel.device_a.name, {})
    device_a_ip        = device_a_info.get("management_ip")
    device_a_last_ip   = device_a_info.get("last_ip")
    device_b_info      = mgmt_map.get(tunnel.device_b.name, {})
    device_b_ip        = device_b_info.get("management_ip")
    device_b_last_ip   = device_b_info.get("last_ip")


    if any(name not in mgmt_map for name in device_names):
        return {"status": "error", "message": "Failed to fetch management IPs"}
    print(">>> mgmt_map:", mgmt_map)

    # 4) PSK generation
    if not tunnel.pre_shared_key:
        tunnel.pre_shared_key = generate_psk(tunnel)
 
    # 5) Subnet allocation
 
   
    # 6-8) Render, push, record
    last_hash = None
    tunnel.save(update_fields=['pre_shared_key'])
    mgmt_ip_a = device_a_ip
    if not tunnel.device_a_wan_ip:
        device_a_ip_network = get_ip_config_by_mgmt_ip(mgmt_ip_a)
        wan_list = device_a_ip_network.get("data", {}).get("local_wan_ip", [])
        if wan_list:
            device_a_wan_ip = wan_list[0]["ip"]
        else:
            device_a_wan_ip = None
        
        if device_a_wan_ip:
            tunnel.device_a_wan_ip = device_a_wan_ip
            tunnel.save(update_fields=['device_a_wan_ip'])


    mgmt_ip_b = device_b_ip
    print(">>> mgmt_ip_b:", mgmt_ip_b)
    if not tunnel.device_b_wan_ip:
        device_b_ip_network= get_ip_config_by_mgmt_ip(mgmt_ip_b)
        
        wan_list_b = device_b_ip_network.get("data", {}).get("local_wan_ip", [])
        if wan_list_b:
            device_b_wan_ip = wan_list_b[0]["ip"]
        else:
            device_b_wan_ip = None
        
        if device_b_wan_ip:
            tunnel.device_b_wan_ip = device_b_wan_ip
            tunnel.save(update_fields=['device_b_wan_ip'])

     




   
    

    print(">>> payload:")
    print(">>> device_a_ip_network:",{tunnel.device_a_wan_ip})
    print(">>> device_b_ip_network:",{tunnel.device_b_wan_ip})
 

# or whatever makes sense: 'pending', 'down', etc.
  
    
   
 
   
    

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
