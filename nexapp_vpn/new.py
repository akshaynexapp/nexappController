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

    device_names = [tunnel.device_a.name] + [d.name for d in tunnel.device_b.all()]
    print(">>> Device names:", device_names)
    online = fetch_online_devices_by_names(device_names)
    if len(online) != len(device_names):
        print(">>> erro online devices:", online)
        return {"status": "error", "message": "Not all devices are online"}
    



    # 3) Discover management IPs
    mgmt_map = fetch_management_ips_by_names(device_names)
  
    if any(name not in mgmt_map for name in device_names):
        return {"status": "error", "message": "Failed to fetch management IPs"}
    print(">>> mgmt_map:", mgmt_map)



    # 4) PSK generation
    if not tunnel.pre_shared_key:
        tunnel.pre_shared_key = generate_psk(tunnel)
 
 
    # 6-8) Render, push, record
    last_hash = None
    tunnel.save(update_fields=['pre_shared_key'])
    mgmt_ip_a = mgmt_map.get(tunnel.device_a.name)
    if not tunnel.device_a_wan_ip:
        device_a_ip_network = get_ip_config_by_mgmt_ip(mgmt_ip_a)
        print("device_a",device_a_ip_network)
        data_a = device_a_ip_network.get('data', {})
        device_a_wan_ip = data_a.get('local_wan_ip')
        print(f">>> WAN IP: {device_a_wan_ip}, Subnet: {tunnel.device_a_subnet}")
        tunnel.device_a_wan_ip = device_a_wan_ip
        tunnel.save(update_fields=['device_a_wan_ip', 'device_a_subnet'])

    mgmt_ip_b = mgmt_map.get(tunnel.device_b.first().name)
    # for spoke in tunnel.device_b.all():
    #     mgmt_ip_b = mgmt_map.get(spoke.name)
    print(">>> mgmt_ip_b:", mgmt_ip_b)
    if not tunnel.device_b_wan_ip:
        device_b_ip_network= get_ip_config_by_mgmt_ip(mgmt_ip_b)
    
        print("device_b",device_b_ip_network)
        data_b = device_b_ip_network.get('data', {})
        device_b_wan_ip = data_b.get('local_wan_ip')
        print(f">>> WAN IP: {device_b_wan_ip}, Subnet: {tunnel.device_b_subnet}")
        tunnel.device_b_wan_ip = device_b_wan_ip
        tunnel.save(update_fields=['device_b_wan_ip'])

    # payload_a = {
    #      "ns_name": tunnel.name,
    #         "ike": {
    #           "hash_algorithm": tunnel.ike_integrity_algorithm,
    #           "encryption_algorithm": tunnel.ike_encryption_algorithm,
    #           "dh_group": tunnel.ike_diffie_hellman_group,
    #           "rekeytime": tunnel.ike_key_lifetime
    #         },
    #         "esp": {
    #           "hash_algorithm": tunnel.esp_integrity_algorithm,
    #           "encryption_algorithm": tunnel.esp_encryption_algorithm,
    #           "dh_group": tunnel.esp_diffie_hellman_group,
    #           "rekeytime": tunnel.esp_key_lifetime
    #         },
    #         "ipcomp":  "true" if tunnel.ipcomp else "false",
    #         "enabled": "1"    if tunnel.is_enabled else "0",
    #         "dpdaction": tunnel.dpdaction,
    #         "keyexchange": tunnel.ike_version,
    #         "local_subnet": [tunnel.device_a_subnet],
    #         "remote_subnet": [tunnel.device_b_subnet],
    #         "gateway": mgmt_ip_b,
    #         "local_identifier": tunnel.local_identifier, #HUB
    #         "remote_identifier": tunnel.remote_identifier,  #Branch
    #         "local_ip": mgmt_ip_a,
    #         "pre_shared_key": tunnel.pre_shared_key
    
    # }
     
    # payload_b =  {
    #      "ns_name": tunnel.name,
    #         "ike": {
    #           "hash_algorithm": tunnel.ike_integrity_algorithm,
    #           "encryption_algorithm": tunnel.ike_encryption_algorithm,
    #           "dh_group": tunnel.ike_diffie_hellman_group,
    #           "rekeytime": tunnel.ike_key_lifetime
    #         },
    #         "esp": {
    #           "hash_algorithm": tunnel.esp_integrity_algorithm,
    #           "encryption_algorithm": tunnel.esp_encryption_algorithm,
    #           "dh_group": tunnel.esp_diffie_hellman_group,
    #           "rekeytime": tunnel.esp_key_lifetime
    #         },
    #         "ipcomp":  "true" if tunnel.ipcomp else "false",
    #         "enabled": "1"    if tunnel.is_enabled else "0",
    #         "dpdaction": tunnel.dpdaction,
    #         "keyexchange": tunnel.ike_version,
    #         # "remote_subnet": [self.remote_subnet],
    #         # "local_subnet":  [self.local_subnet],
    #         "local_subnet": [tunnel.device_b_subnet],
    #         "remote_subnet": [tunnel.device_a_subnet],
    #         "gateway": mgmt_ip_a,
    #         "local_identifier": tunnel.local_identifier,
    #         "remote_identifier": tunnel.remote_identifier,
    #         "local_ip": mgmt_ip_b,
    #         "pre_shared_key": tunnel.pre_shared_key
    
    # }
    #     # last_hash = hashlib.sha256(payload_a.encode()).hexdigest()

    # Push config to device
    payload_calls = get_ipsec_payloads(tunnel,mgmt_ip_b, mgmt_ip_a)

    print(">>> payload:")
    print(">>> payload:, payload_calls", payload_calls)
    if tunnel.device_a_wan_ip and tunnel.device_b_wan_ip and payload_calls:



        # res_a = push_ipsec_config_by_mgmt_ip(mgmt_ip_a, payload_a)
        # if not res_a:
        #     return {
        #         'status': 'error',
        #         'message': f"Failed to push config to {tunnel.device_a.name}"
        #     }
        # print(">>> res_a:", res_a)
        
        
        
        # res_b = push_ipsec_config_by_mgmt_ip(mgmt_ip_b, payload_b)
        # if not res_b:   
        #     return {
        #         'status': 'error',
        #         'message': f"Failed to push config to {tunnel.device_b.first().name}"
        #     }
        # print(">>> res_b:", res_b)
        
        results = []
        for call in payload_calls:
            host = call['payload']['local_ip']
            url  = f"https://{host}/api-new/ipsec"
            resp = requests.post(
                url,
                json=call,
                verify=False,
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
        
        # 3. Extract the API’s own 'code' field (if any)
            api_code = data.get("code")
            results.append({
                "host":     host,
                "api_code": api_code,
                "body":     data
            })   
 
        if all(r["api_code"] == 200 for r in results):
            last_hash = hashlib.sha256(str(payload_calls).encode()).hexdigest()
            tunnel.last_pushed_at    = timezone.now()
            tunnel.last_config_hash  = last_hash
            tunnel.save()
            def get_connected_flag(response, name):
                for entry in response.get('data', {}).get('tunnels', []):
                    if entry.get('name') == name:
                        return entry.get('connected', False)
        # return False
    # …later in your code…
                verify   = get_ipsec_config_by_mgmt_ip(mgmt_ip_a)
                connected_a = get_connected_flag(verify, tunnel.name)
                
                verify_b  = get_ipsec_config_by_mgmt_ip(mgmt_ip_b)
                connected_b = get_connected_flag(verify_b, tunnel.name)
                
                print(">>> connected_a:", connected_a)
                print(">>> connected_b:", connected_b)
                if connected_a and connected_b:
                    tunnel.status = 'active'
                    tunnel.save()
                    return {
                    'status': 'error',
                    'message': (
                        f"Tunnel '{tunnel.name}' is active "
                        f"to {tunnel.device_a.name}"
                    )
                  }
               
                else:
                    tunnel.status = 'error'
                    tunnel.save()
                    return {
                    'status': 'error',
                    'message': 
                        f"Tunnel '{tunnel.name}' pushed but not active "
                   
                
                }

            
        else:
            for r in results:
                if r["api_code"] != 200:
                    print(f"{r['host']} failed with code {r['api_code']}")
        
           
            # tunnel.status = 'active'
    
           
    else:
        # last_hash = hashlib.sha256(str(payload_a).encode()).hexdigest()
        # tunnel.last_pushed_at = timezone.now()
        # tunnel.last_config_hash = last_hash
        # tunnel.status = 'active'
        return {
            'status': 'error',
            'message':
                f"Tunnel '{tunnel.name}' failed to get IP "
             
            
        }
    
    

# or whatever makes sense: 'pending', 'down', etc.
  
    
   
 
   
    


def rollback_site_to_site(tunnel_id, to_hash=None):
    from sdwan_tunnel.models import Tunnel, ConfigHistory, TunnelStatus

    """
    Roll back the tunnel config to the last known good state or a given hash.
    """
    tunnel = Tunnel.objects.get(id=tunnel_id)
    # Select history entry
    history_qs = ConfigHistory.objects.filter(tunnel=tunnel)
    if to_hash:
        history_qs = history_qs.filter(payload_hash=to_hash)
    history = history_qs.order_by('-timestamp').first()

    if not history:
        structured_log('site2site.rollback.failed', tunnel_id=tunnel.id, reason='no_history')
        return {'status': 'error', 'message': 'No history available to roll back.'}

    cid = structured_log('site2site.rollback.started', tunnel_id=tunnel.id)
    payload = history.payload.get('config') if isinstance(history.payload, dict) else history.payload

    for peer in tunnel.device_peers.all():
        device = peer.local_device
        try:
            result = push_config(device, payload, vpn_type='ipsec', correlation_id=cid)
            success = result.get('status') != 'error'
        except Exception as e:
            structured_log('site2site.rollback.error', device_id=device.id, error=str(e), correlation_id=cid)
            success = False

        # Record rollback history
        ConfigHistory.objects.create(
            user=history.user,
            tunnel=tunnel,
            payload_hash=history.payload_hash,
            payload=history.payload,
            config_text=history.config_text,
            action='rollback'
        )

        TunnelStatus.objects.create(
            tunnel=tunnel,
            is_up=success,
            latency_ms=None,
            packet_loss_percent=None
        )

    structured_log('site2site.rollback.completed', tunnel_id=tunnel.id, correlation_id=cid)
    structured_log('site2site.rollback.recorded', tunnel_id=tunnel.id, correlation_id=cid)
    tunnel.status = 'active'
    tunnel.save()

    return {'status': 'success', 'tunnel_id': tunnel.id, 'action': 'rollback'}