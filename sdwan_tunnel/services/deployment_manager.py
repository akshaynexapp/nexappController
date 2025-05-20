# sdwan_tunnel/services/deployment_manager.py
"""
Orchestrates the full Site-to-Site IPsec deployment flow.
Invokes protocol handlers and background tasks as needed.
"""
from sdwan_tunnel.protocols.ipsec.handlers.site_to_site import deploy_site_to_site, rollback_site_to_site
from sdwan_tunnel.utils.logging_utils import structured_log



 
def deploy_vpn_topology(data, user):
    """
    Entry point for deploying VPN topologies.
 
    For Phase 1 (Site-to-Site IPsec), expects:
    - data: {'tunnel_id': <int>, 'full_replace': <bool>}
    """
    tunnel_id    = data.get('tunnel_id')
    full_replace = data.get('full_replace', False)
    cid = structured_log('deployment_manager.start',
                         tunnel_id=tunnel_id, user_id=user.id)
    try:
        result = deploy_site_to_site(tunnel_id, full_replace)
        structured_log('deployment_manager.success',
                       tunnel_id=tunnel_id, correlation_id=cid)
        return result
    except Exception as e:
        structured_log('deployment_manager.error',
                       tunnel_id=tunnel_id, error=str(e), correlation_id=cid)
        # Attempt rollback on failure
        try:
            rollback_site_to_site(tunnel_id)
        except Exception:
            pass
        return {'status': 'error', 'message': str(e)}