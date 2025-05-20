
# sdwan_tunnel/services/config_fetch.py
import requests
from sdwan_tunnel.utils.logging_utils import structured_log

def fetch_config(device, vpn_type, correlation_id=None):
    mgmt_ip = device.management_ip
    url = f"https://{mgmt_ip}/api-new/{vpn_type}"
    cid = structured_log('config_fetch.start', device_id=device.id, vpn_type=vpn_type, correlation_id=correlation_id)
    resp = requests.post(url, json={'method':'get-config','payload':{}}, timeout=10, verify=True)
    resp.raise_for_status()
    structured_log('config_fetch.complete', device_id=device.id, correlation_id=cid)
    return resp.json().get('data', {})

