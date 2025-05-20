
# sdwan_tunnel/services/subnet_allocate.py
"""
IPAM for tunnel link subnets.
"""
import ipaddress
from sdwan_tunnel.utils.logging_utils import structured_log

# Simple in-memory pool (replace with DB-backed IPAM in prod)
POOL = ipaddress.ip_network('10.100.0.0/16')
ALLOCATED = set()

def allocate_subnet(tunnel, prefix=30):
    cid = structured_log('subnet_allocate.start', tunnel_id=tunnel.id)
    for subnet in POOL.subnets(new_prefix=prefix):
        net = str(subnet)
        if net in ALLOCATED:
            continue
        ALLOCATED.add(net)
        hosts = list(subnet.hosts())
        a, b = str(hosts[0]), str(hosts[1])
        structured_log('subnet_allocate.complete', tunnel_id=tunnel.id, subnet=net, correlation_id=cid)
        return net, a, b
    raise RuntimeError('No free subnets')


def release_subnet(tunnel):
    cid = structured_log('subnet_allocate.release.start', tunnel_id=tunnel.id)
    ALLOCATED.discard(tunnel.subnet)
    structured_log('subnet_allocate.release.complete', tunnel_id=tunnel.id, correlation_id=cid)
