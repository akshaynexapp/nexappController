from django.apps import AppConfig
from openwisp_utils.admin_theme.menu import register_menu_group, register_menu_subitem
from swapper import get_model_name
from django.utils.translation import gettext_lazy as _


class TrafficApplicationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'traffic_application'
    label       = 'traffic_application'
    
    verbose_name= _('Traffic & Application')

    def ready(self):
        self.register_menu_groups3()
        

    def register_menu_groups3(self):
        register_menu_group(
            position=47,  # adjust to fit your menu order
            config={
                'label': _('Traffic & Application'),
                'icon': 'ow-trafficapplication-icon',
                'items': {
                    1: {
                        'label': _('Firewall'),
                        'model': get_model_name('traffic_application', 'Firewall'),
                        'name': 'changelist',
                        'icon': 'ow-sdwanfirewall-icon',
                    },
                    2: {
                        'label': _('Application'),
                        'model': get_model_name('traffic_application', 'Application'),
                        'name': 'changelist',
                        'icon': 'ow-trafficapp-icon',
                    },
                    
                },
            },
        )
    