from django.apps import AppConfig
from swapper import get_model_name
from openwisp_utils.admin_theme.menu import register_menu_group, register_menu_subitem

from django.utils.translation import gettext_lazy as _

class SdwanTunnelConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name        = 'sdwan_tunnel'
    label       = 'sdwan_tunnel'
    verbose_name= _('SD-WAN Tunnel')

    def ready(self):
        self.register_menu_groups()
        

    def register_menu_groups(self):
        register_menu_group(
            position=45,
            config={
                'label': _('Tunnel'),
                'icon': 'ow-tunnel-icon',
                'items': {
                    1: {
                        'label': _('Site-to-Site'),
                        'model': get_model_name('sdwan_tunnel', 'Tunnel'),
                        'name': 'changelist',
                        'icon': 'ow-site-to-site-icon',
                    },
                    2: {
                        'label': _('Hub'),
                        'model': get_model_name('sdwan_tunnel', 'Hub'),
                        'name': 'changelist',
                        'icon': 'ow-hub-icon',
                    },
                    3: {
                        'label': _('Peer'),
                        'model': get_model_name('sdwan_tunnel', 'Spoke'),
                        'name': 'changelist',
                        'icon': 'ow-spoke-icon',
                    },
                    4: {
                        'label': _('Jobs'),
                        'model': get_model_name('sdwan_tunnel', 'Job'),
                        'name': 'changelist',
                        'icon': 'ow-job-icon',
                    },
                    5: {
                        'label': _('Path Label'),
                        'model': get_model_name('sdwan_tunnel', 'PathLabel'),
                        'name': 'changelist',
                        'icon': 'ow-pathlabel-icon',
                    },
                   
                    6: {
                        'label': _('Link Monitoring'),
                        'model': get_model_name('sdwan_tunnel', 'LinkMonitoring'),
                        'name': 'changelist',
                        'icon': 'ow-linkmonitoring-icon',
                    },
                   

                },
            }
        )
  
    
    
    
   

    