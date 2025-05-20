
# sdwan_tunnel/services/failover_manager.py
from sdwan_tunnel.models import Tunnel
from sdwan_tunnel.services.monitor import poll_status
from sdwan_tunnel.utils.logging_utils import structured_log

def evaluate_failover(topology_id):
    """
    Checks all tunnels in a topology and re-routes traffic if primary fails.
    Phase 1: stub that marks any down tunnel as 'error'.
    """
    cid = structured_log('failover.start', topology_id=topology_id)
    for tunnel in Tunnel.objects.filter(topology_id=topology_id):
        data = poll_status(tunnel.device_a, tunnel.vpn_type)
        if not data.get('is_up'):
            tunnel.status = 'error'
            tunnel.save(update_fields=['status'])
            structured_log('failover.executed', tunnel_id=tunnel.id, correlation_id=cid)
    structured_log('failover.complete', topology_id=topology_id, correlation_id=cid)
    return {'status':'complete'}