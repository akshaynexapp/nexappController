# sdwan_tunnel/services/config_modify.py
from jinja2 import Environment, FileSystemLoader
import os
from sdwan_tunnel.utils.logging_utils import structured_log

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLDIR = os.path.join(BASE, 'protocols', 'ipsec', 'templates')
env = Environment(loader=FileSystemLoader(TEMPLDIR), autoescape=False)

def render_config(device, tunnel, vpn_type, full_replace=False, correlation_id=None):
    # cid = structured_log('config_modify.start', tunnel_id=tunnel.id, device_id=device.id, correlation_id=correlation_id)
    tpl = env.get_template('config.j2')
    payload = tpl.render(device=device, tunnel=tunnel)
    # structured_log('config_modify.complete', correlation_id=cid)
    return payload
