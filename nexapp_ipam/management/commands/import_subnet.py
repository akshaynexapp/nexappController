import swapper

from . import BaseImportSubnetCommand


class Command(BaseImportSubnetCommand):
    subnet_model = swapper.load_model('nexapp_ipam', 'Subnet')
