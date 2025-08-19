# sdwan_tunnel/api.py
import requests
from requests.exceptions import RequestException

TIMEOUT = 15  # seconds

class TunnelAPIError(Exception):
    pass

def delete_tunnel_by_name(tunnel_name, mng_ip):
    """
    1) hits https://{mng_ip}/api-new/ipsec with get-config
    2) finds the matching tunnel by name
    3) hits the same URL with delete-tunnel
    """
    url = f"https://{mng_ip}/api-new/ipsec"
    if not mng_ip or str(mng_ip).lower() == 'none':
        return True
    # 1) GET-CONFIG
    try:
        resp = requests.post(
            url,
            json={'method': 'get-config', 'payload': {}},
            timeout=TIMEOUT,
            verify=False,
        )
        resp.raise_for_status()
        body = resp.json()
    except RequestException as e:
        raise TunnelAPIError(f"get-config request failed: {e}")
    except ValueError as e:
        raise TunnelAPIError(f"get-config response JSON decode failed: {e}")

    if body.get('code') != 200:
        raise TunnelAPIError(f"get-config failed: {body!r}")
    # 2) locate our tunnel
    tunnels = body.get('data', {}).get('tunnels', [])
    match = next((t for t in tunnels if t.get('name') == tunnel_name), None)
    if not match:
        raise TunnelAPIError(f"No tunnel named {tunnel_name!r} on {mng_ip}")
    if not match:
        # no tunnel to delete externally, but we still want to delete locally
        return True

    tunnel_id = match['id']

    # 3) DELETE-TUNNEL
    try:
        resp2 = requests.post(
            url,
            json={'method': 'delete-tunnel', 'payload': {'id': tunnel_id}},
            timeout=TIMEOUT,
            verify=False,
        )
        resp2.raise_for_status()
        body2 = resp2.json()
    except RequestException as e:
        raise TunnelAPIError(f"delete-tunnel request failed: {e}")
    except ValueError as e:
        raise TunnelAPIError(f"delete-tunnel response JSON decode failed: {e}")

    if body2.get('code') != 200:
        raise TunnelAPIError(f"delete-tunnel failed: {body2!r}")

    return True