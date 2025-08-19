import os
import hashlib ,requests
from django.utils import timezone
from sdwan_tunnel.tasks.hub_spoke_helpers import get_hub_spoke_ipsec_payloads
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
  

    # 1) Load tunnel, hub & spokes
    tunnel = Tunnel.objects.get(id=tunnel_id)
    hub     = tunnel.device_a
    spokes  = tunnel.device_b.all()

    # 2) Ensure all devices are online
    device_names = [hub.name] + [s.name for s in spokes]
    online = fetch_online_devices_by_names(device_names)
    if len(online) != len(device_names):
        return {"status": "error", "message": "Not all devices are online"}

    # 3) Fetch management IPs
    mgmt_map = fetch_management_ips_by_names(device_names)
    if any(name not in mgmt_map for name in device_names):
        return {"status": "error", "message": "Failed to fetch management IPs"}
    hub_ip = mgmt_map[hub.name]

    # 4) Ensure PSK exists
    if not tunnel.pre_shared_key:
        tunnel.pre_shared_key = generate_psk(tunnel)
        tunnel.save(update_fields=["pre_shared_key"])

    # 5) Populate WAN IPs if missing
    if not tunnel.device_a_wan_ip:
        info = get_ip_config_by_mgmt_ip(hub_ip)
        tunnel.device_a_wan_ip = info["data"].get("local_wan_ip")
        tunnel.save(update_fields=["device_a_wan_ip"])

    wan_ip_map = {}
    for spoke in spokes:
        mgmt_ip_b = mgmt_map[spoke.name]
        info      = get_ip_config_by_mgmt_ip(mgmt_ip_b)
        spoke_wan = info["data"].get("local_wan_ip")
        wan_ip_map[spoke.name] = spoke_wan

        # OPTIONAL: if your Device model has a 'wan_ip' field, you could persist:
        # spoke.wan_ip = spoke_wan
        # spoke.save(update_fields=["wan_ip"])

    print("Finished populating WAN IPs")
    print("subnet A:", tunnel.device_a_subnet, "WAN IP A:", tunnel.device_a_wan_ip)
    for spoke in spokes:
        spoke_subnet = getattr(spoke, "device_b_subnet", "<no-subnet-field>")
        print(f"subnet B ({spoke.name}): {spoke_subnet}, WAN IP B ({spoke.name}): {wan_ip_map[spoke.name]}")

    # 6) Build payloads
    payloads = get_hub_spoke_ipsec_payloads(tunnel)
    print("Generated payloads:", payloads)
    results = []
    all_ok  = True
    pushed  = set()

    for entry in payloads:
        device  = entry["device"]
        payload = entry["payload"]
        host    = hub_ip if device == hub.name else wan_ip_map[device]
    
        if host in pushed:
            continue
        pushed.add(host)
    
        # wrap in the RPC envelope the API expects:
        rpc_call = {
            "method":  "set-config",
            "payload": payload
        }
    
        try:
            resp = requests.post(
                f"https://{host}/api-new/ipsec_server",
                json=rpc_call,              # <— send the envelope, not just payload
                verify=False,
                timeout=30
            )
            resp.raise_for_status()
            body = resp.json()
    
            # Debug print the server’s echo of your request:
            print(f"[DEBUG] Server echoed: {body.get('method')}, payload = {body.get('payload')}")

            code = body.get("code", body.get("payload",{}).get("code"))
            results.append({"device": device, "host": host, "code": code, "body": body})
            if code != 200:
                all_ok = False
    
        except Exception as e:
            results.append({"device": device, "host": host, "error": str(e)})
            all_ok = False
    # 8) Record push metadata
    if all_ok:
        tunnel.last_pushed_at   = timezone.now()
        tunnel.last_config_hash = hashlib.sha256(str(results).encode()).hexdigest()
        tunnel.save(update_fields=["last_pushed_at", "last_config_hash"])
    else:
        tunnel.status = "error"
        tunnel.save(update_fields=["status"])
        return {"status": "error", "results": results}

    # 9) Verify connectivity
    def get_connected_flag(resp, name):
        for t in resp.get("data", {}).get("tunnels", []):
            if t.get("name") == name:
                return t.get("connected", False)
        return False

    verify_a    = get_ipsec_config_by_mgmt_ip(hub_ip)
    connected_a = get_connected_flag(verify_a, tunnel.name)

    connected_all = True
    for spoke in spokes:
        ip_b       = mgmt_map[spoke.name]
        verify_b   = get_ipsec_config_by_mgmt_ip(ip_b)
        if not get_connected_flag(verify_b, tunnel.name):
            connected_all = False

    # 10) Final status & return
    if connected_a and connected_all:
        tunnel.status = "active"
        tunnel.save(update_fields=["status"])
        return {
            "status": "success",
            "message": f"Tunnel '{tunnel.name}' is active across hub and all spokes."
        }
    else:
        tunnel.status = "error"
        tunnel.save(update_fields=["status"])
        return {
            "status": "error",
            "message": f"Tunnel '{tunnel.name}' pushed but not fully active.",
            "results": results
        }