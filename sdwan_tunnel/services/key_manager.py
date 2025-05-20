# sdwan_tunnel/services/key_manager.py
"""
Cryptographic key and certificate management.
"""
import secrets
from sdwan_tunnel.utils.logging_utils import structured_log


def generate_psk(tunnel):
    cid = structured_log('key_manager.generate_psk.start', tunnel_id=tunnel.id)
    pre_shared_key = secrets.token_urlsafe(32)
    tunnel.pre_shared_key = pre_shared_key 
    tunnel.save(update_fields=['pre_shared_key'])
    structured_log('key_manager.generate_psk.complete', tunnel_id=tunnel.id, correlation_id=cid)
    return pre_shared_key


def generate_wg_keys(device):
    # Placeholder for WireGuard key generation
    cid = structured_log('key_manager.generate_wg_keys.start', device_id=device.id)
    private = secrets.token_urlsafe(32)
    public = '<derive from private>'
    structured_log('key_manager.generate_wg_keys.complete', device_id=device.id, correlation_id=cid)
    return private, public
