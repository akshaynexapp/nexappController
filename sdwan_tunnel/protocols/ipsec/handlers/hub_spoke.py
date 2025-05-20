import os
import hashlib ,requests
from django.utils import timezone
from sdwan_tunnel.tasks.helpers import get_ipsec_payloads
from jinja2 import Environment, FileSystemLoader
from sdwan_tunnel.services.key_manager import generate_psk

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



def deploy_hub_and_spoke(tunnel_id, full_replace=False):
    from sdwan_tunnel.models.tunnel import Tunnel
    from sdwan_tunnel.models.config_history import ConfigHistory
    from sdwan_tunnel.models.tunnel_status import TunnelStatus
  
    tunnel = Tunnel.objects.get(id=tunnel_id)
    hub = tunnel.device_a
    spokes = tunnel.device_b.all()

    device_names = [hub.name] + [spoke.name for spoke in spokes]
    online = fetch_online_devices_by_names(device_names)
    if len(online) != len(device_names):
        return {"status": "error", "message": "Not all devices are online"}

    mgmt_map = fetch_management_ips_by_names(device_names)
    if any(name not in mgmt_map for name in device_names):
        return {"status": "error", "message": "Failed to fetch management IPs"}

    if not tunnel.pre_shared_key:
        tunnel.pre_shared_key = generate_psk(tunnel)

  

    tunnel.save(update_fields=['pre_shared_key'])

    mgmt_ip_a = mgmt_map[hub.name]
    if not tunnel.device_a_wan_ip:
        hub_ip_info = get_ip_config_by_mgmt_ip(mgmt_ip_a)
        tunnel.device_a_wan_ip = hub_ip_info['data'].get('local_wan_ip')
        tunnel.save(update_fields=['device_a_wan_ip'])

    results = []
    all_success = True
    pushed_hosts = set()  # Move this outside spoke loop if needed across spokes

    for spoke in spokes:
        spoke_name = spoke.name
        mgmt_ip_b = mgmt_map.get(spoke_name)
        print("inside spoke loop")
        # Fetch WAN IP for the spoke
        if not tunnel.device_b_wan_ip:
            spoke_ip_info = get_ip_config_by_mgmt_ip(mgmt_ip_b)
            tunnel.device_b_wan_ip = spoke_ip_info['data'].get('local_wan_ip')
            tunnel.save(update_fields=['device_b_wan_ip'])

        # Generate config payload per spoke
        payloads = get_ipsec_payloads(tunnel, mgmt_ip_b, mgmt_ip_a)
        print("payloads",payloads)
        for call in payloads:
            host = call['payload']['local_ip']
            if host in pushed_hosts:
                continue
            pushed_hosts.add(host)
            try:
                resp = requests.post(
                    f"https://{host}/api-new/ipsec",
                    json=call,
                    verify=False,
                    timeout=30
                )
                resp.raise_for_status()
                body = resp.json()
                api_code = body.get("code")

                results.append({
                    "spoke": spoke_name,
                    "host": host,
                    "api_code": api_code,
                    "body": body
                })

                if api_code != 200:
                    all_success = False

            except Exception as e:
                results.append({
                    "spoke": spoke_name,
                    "host": host,
                    "error": str(e)
                })
                all_success = False
    print("results",results)
    if all_success:
        tunnel.last_pushed_at = timezone.now()
        tunnel.last_config_hash = hashlib.sha256(str(results).encode()).hexdigest()
    #     def get_connected_flag(response, name):
    #             for entry in response.get('data', {}).get('tunnels', []):
    #                 if entry.get('name') == name:
    #                     return entry.get('connected', False)
    #     # return False
    # # …later in your code…
    #             verify   = get_ipsec_config_by_mgmt_ip(mgmt_ip_a)
    #             connected_a = get_connected_flag(verify, tunnel.name)
                
    #             verify_b  = get_ipsec_config_by_mgmt_ip(mgmt_ip_b)
    #             connected_b = get_connected_flag(verify_b, tunnel.name)
                
    #             print(">>> connected_a:", connected_a)
    #             print(">>> connected_b:", connected_b)
    #             if connected_a and connected_b:
    #                 tunnel.status = 'active'
    #                 tunnel.save()
    #                 return {
    #                 'status': 'error',
    #                 'message': (
    #                     f"Tunnel '{tunnel.name}' is active "
    #                     f"to {tunnel.device_a.name}"
    #                 )
    #               }
               
    #             else:
    #                 tunnel.status = 'error'
    #                 tunnel.save()
    #                 return {
    #                 'status': 'error',
    #                 'message': 
    #                     f"Tunnel '{tunnel.name}' pushed but not active "
                   
                
    #             }


        

        def get_connected_flag(response, name):
            for entry in response.get('data', {}).get('tunnels', []):
                if entry.get('name') == name:
                    return entry.get('connected', False)
            return False

        verify_a = get_ipsec_config_by_mgmt_ip(mgmt_ip_a)
        connected_a = get_connected_flag(verify_a, tunnel.name)
    
        connected_all = True
        for spoke in spokes:
            mgmt_ip_b = mgmt_map[spoke.name]
            verify_b = get_ipsec_config_by_mgmt_ip(mgmt_ip_b)
            connected_b = get_connected_flag(verify_b, tunnel.name)
            print(f">>> {spoke.name} connected_b: {connected_b}")
            if not connected_b:
                connected_all = False
    
        if connected_a and connected_all:
            tunnel.status = 'active'
            tunnel.save()
            return {
                'status': 'success',
                'message': f"Tunnel '{tunnel.name}' is active across hub and all spokes."
            }
        else:
            tunnel.status = 'error'
            tunnel.save()
            return {
                'status': 'error',
                'message': f"Tunnel '{tunnel.name}' pushed but not fully active."
            }
    

    else:
        tunnel.status = 'error'
        tunnel.save()
        return {
            'status': 'error',
            'message': 'One or more spoke pushes failed.',
            'results': results
        }
