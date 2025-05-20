# sdwan_tunnel/services/rollback_manager.py
"""
Provides a generic rollback entrypoint for device configurations.
"""
from sdwan_tunnel.protocols.ipsec.handlers.site_to_site import rollback_site_to_site
from sdwan_tunnel.utils.logging_utils import structured_log


def rollback_device(device, vpn_type, to_hash=None):
    """
    Roll back the given tunnel (identified by device and type) to a prior config.
    For Phase 1, uses Site-to-Site IPsec rollback.
    """
    # device here maps to tunnel.primary endpoint; find tunnel
    tunnel = device.device_peers.first().tunnel
    cid = structured_log('rollback_manager.start', tunnel_id=tunnel.id, device_id=device.id)
    result = rollback_site_to_site(tunnel.id, to_hash)
    structured_log('rollback_manager.complete', tunnel_id=tunnel.id, correlation_id=cid)
    return result
