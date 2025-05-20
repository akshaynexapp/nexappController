
# sdwan_tunnel/services/topology_manager.py
"""
Generate tunnel definitions based on OpenWISP topology and requested VPN types.
For Phase 1, builds a list of tunnel IDs for site-to-site IPsec.
"""
from sdwan_tunnel.integration.openwisp_adapter import list_org_topologies, list_org_devices
from sdwan_tunnel.models import Tunnel, DevicePeer
from sdwan_tunnel.utils.logging_utils import structured_log


def build_tunnels_for_topology(topology_id, vpn_types, user):
    cid = structured_log('topology_manager.start', topology_id=topology_id, user_id=user.id)
    # Fetch devices participating in this topology
    devices = list_org_devices(user.organizationuser.organization.id)
    tunnels = []
    if 'ipsec' in vpn_types:
        # For each adjacent pair in site-to-site, create Tunnel entries
        for a, b in _pairwise(devices):
            tunnel = Tunnel.objects.create(
                organization=user.organizationuser.organization,
                name=f"{a.name}-{b.name}",
                vpn_type='ipsec', mode='site_to_site', created_by=user,
                device_a=a
            )
            DevicePeer.objects.bulk_create([
                DevicePeer(tunnel=tunnel, local_device=a, peer_device=b, link_subnet='', local_role='hub', peer_role='spoke'),
                DevicePeer(tunnel=tunnel, local_device=b, peer_device=a, link_subnet='', local_role='spoke', peer_role='hub'),
            ])
            tunnels.append(tunnel.id)
    structured_log('topology_manager.complete', topology_id=topology_id, correlation_id=cid)
    return tunnels


def _pairwise(devices):
    """Return adjacent pairs for site-to-site."""
    for i in range(len(devices)-1):
        yield devices[i], devices[i+1]
