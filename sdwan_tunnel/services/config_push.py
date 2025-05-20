# sdwan_tunnel/services/config_push.py
import requests
from sdwan_tunnel.utils.logging_utils import structured_log

def push_config(device, payload, vpn_type, correlation_id=None):
    mgmt_ip = device.management_ip
    url = f"https://{mgmt_ip}/api-new/{vpn_type}"
    cid = structured_log('config_push.start', device_id=device.id, vpn_type=vpn_type, correlation_id=correlation_id)
    resp = requests.post(url, json={'method':'set-config','payload':payload}, timeout=10, verify=False)
    resp.raise_for_status()
    structured_log('config_push.complete', correlation_id=cid)
    return resp.json()
