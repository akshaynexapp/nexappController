# sdwan_tunnel/integration/zerotier_client.py
"""
ZeroTier API wrapper: fetch management IPs for devices via ZeroTier network.
"""
import requests
from django.conf import settings
from sdwan_tunnel.utils.logging_utils import structured_log
 
ZT_API_URL = 'https://my.zerotier.api/v1'
ZT_TOKEN = settings.ZEROTIER_TOKEN
 
 
def get_management_ip(device):
    """Return the ZeroTier-assigned IP address for the given device."""
    cid = structured_log('zerotier_client.request', device_id=device.id)
    url = f"{ZT_API_URL}/network/{device.zerotier_network_id}/member/{device.zerotier_member_id}"
    headers = {'Authorization': f'Bearer {ZT_TOKEN}'}
    resp = requests.get(url, headers=headers, timeout=5)
    resp.raise_for_status()
    data = resp.json()
    mgmt_ip = next((addr for addr in data.get('config', {}).get('assignedAddresses', []) if ':' not in addr), None)
    structured_log('zerotier_client.found', device_id=device.id, mgmt_ip=mgmt_ip, correlation_id=cid)
    return mgmt_ip