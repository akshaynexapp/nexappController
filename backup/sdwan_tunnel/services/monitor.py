# sdwan_tunnel/services/monitor.py
import requests
from sdwan_tunnel.utils.logging_utils import structured_log

def poll_status(device, vpn_type):
    mgmt_ip = device.management_ip
    url = f"https://{mgmt_ip}/api-new/{vpn_type}-status"
    cid = structured_log('monitor.start', device_id=device.id, vpn_type=vpn_type)
    resp = requests.get(url, timeout=10, verify=False)
    resp.raise_for_status()
    data = resp.json().get('data', {})
    structured_log('monitor.complete', correlation_id=cid)
    return data
