import pytest
from sdwan_tunnel.services.key_manager import generate_psk, generate_wg_keys
from sdwan_tunnel.services.subnet_allocate import allocate_subnet, release_subnet, POOL, ALLOCATED
from sdwan_tunnel.models import Tunnel
from django.contrib.auth import get_user_model
from django.utils import timezone
 
User = get_user_model()
 
class DummyTunnel:
    """Simple stand-in for Tunnel model to test key_manager and subnet_allocate"""
    def __init__(self, id):
        self.id = id
        self.psk = None
        self.subnet = None
 
    def save(self, update_fields=None):
        # simulate saving
        pass
 
@pytest.mark.unit
def test_generate_psk_assigns_length():
    t = DummyTunnel(id=1)
    psk = generate_psk(t)
    assert isinstance(psk, str)
    assert len(psk) >= 43  # token_urlsafe(32) produces ~43 chars
    assert t.psk == psk
 
@pytest.mark.unit
def test_generate_wg_keys_returns_pair():
    class DummyDevice:
        id = 1
    priv, pub = generate_wg_keys(DummyDevice())
    assert isinstance(priv, str)
    assert isinstance(pub, str)
 
@pytest.mark.unit
def test_allocate_and_release_subnet():
    # clear any prior allocations
    ALLOCATED.clear()
    dummy = DummyTunnel(id=1)
    subnet, a, b = allocate_subnet(dummy)
    # subnet should be in POOL
    assert subnet in {str(s) for s in POOL.subnets(new_prefix=30)}
    assert subnet in ALLOCATED
    # host IPs should belong to the subnet
    import ipaddress
    net = ipaddress.ip_network(subnet)
    assert ipaddress.ip_address(a) in net
    assert ipaddress.ip_address(b) in net
    # release and ensure removed
    release_subnet(dummy)
    assert subnet not in ALLOCATED
 
# Note: services interacting with HTTP (config_fetch, config_push, etc.)
# should be tested using pytest-mock to stub requests.post/get