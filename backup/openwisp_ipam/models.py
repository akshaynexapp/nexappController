from swapper import swappable_setting

from openwisp_ipam.base.models import AbstractIpAddress, AbstractSubnet


# class Subnet(AbstractSubnet):
#     class Meta(AbstractSubnet.Meta):
#         abstract = False
#         swappable = swappable_setting('nexapp_ipam', 'Subnet')
#         db_table = 'openwisp_ipam_subnet' 


# class IpAddress(AbstractIpAddress):
#     class Meta(AbstractIpAddress.Meta):
#         abstract = False
#         swappable = swappable_setting('nexapp_ipam', 'IpAddress')
#         db_table = 'openwisp_ipam_ipaddress' 

class Subnet(AbstractSubnet):
    class Meta(AbstractSubnet.Meta):
        abstract = False
        app_label = 'nexapp_ipam'  # 👈 you still override the app label
        swappable = swappable_setting('openwisp_ipam', 'Subnet')
        db_table = 'openwisp_ipam_subnet'

class IpAddress(AbstractIpAddress):
    class Meta(AbstractIpAddress.Meta):
        abstract = False
        app_label = 'nexapp_ipam'  # 👈 so it's registered under your new app
        swappable = swappable_setting('openwisp_ipam', 'IpAddress')
        db_table = 'openwisp_ipam_ipaddress'