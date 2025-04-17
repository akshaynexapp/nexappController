import swapper

from . import BaseExportSubnetCommand


class Command(BaseExportSubnetCommand):
    subnet_model = swapper.load_model('nexapp_ipam', 'Subnet')
