from django.db import models

# Create your models here.
from swapper import swappable_setting

from nexapp_ipam.base.models import AbstractIpAddress, AbstractSubnet


class Subnet(AbstractSubnet):
    class Meta(AbstractSubnet.Meta):
        abstract = False
        swappable = swappable_setting('nexapp_ipam', 'Subnet')


class IpAddress(AbstractIpAddress):
    class Meta(AbstractIpAddress.Meta):
        abstract = False
        swappable = swappable_setting('nexapp_ipam', 'IpAddress')
