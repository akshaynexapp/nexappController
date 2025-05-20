"""
Adapter to import and query OpenWISP models: Organization, User, Device, Topology.
Provides helper functions for inventory and topology retrieval.
"""
from openwisp_users.models import Organization, User as OrgUser
from openwisp_controller.config.models import Config as Device, Topology
 
 
def list_org_devices(org_id):
    """Return all devices belonging to the given organization."""
    return Device.objects.filter(organization_id=org_id)
 
 
def list_org_topologies(org_id):
    """Return all topologies belonging to the given organization."""
    return Topology.objects.filter(organization_id=org_id)
 
 
def get_device_credentials(device):
    """Return the management credentials and IP for a device."""
    return {
        'management_ip': device.management_ip,
        'username': device.username,
        'password': device.password
    }