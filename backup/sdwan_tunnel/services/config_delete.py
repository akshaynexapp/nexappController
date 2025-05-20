# sdwan_tunnel/services/config_delete.py
import requests
from sdwan_tunnel.utils.logging_utils import structured_log

def delete_tunnel(device, tunnel_id, vpn_type, correlation_id=None):
    mgmt_ip = device.management_ip
    url = f"https://{mgmt_ip}/api-new/ipsec"
    cid = structured_log('config_delete.start', device_id=device.id, correlation_id=correlation_id)
    resp = requests.post(url, json={'method':'delete-tunnel','payload':{'ns_name':tunnel_id}}, timeout=10, verify=False)
    resp.raise_for_status()
    structured_log('config_delete.complete', correlation_id=cid)
    return resp.json()
