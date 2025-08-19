# from swapper import load_model as swapper_load_model

# from openwisp_notifications.apps import OpenwispNotificationsConfig as AppConfig


# def load_model(model):
#     return swapper_load_model(AppConfig.label, model)

import swapper
from django.core.exceptions import ImproperlyConfigured
from openwisp_notifications.apps import OpenwispNotificationsConfig as AppConfig

def load_model(model_name):
    try:
        # first try under the new label
        return swapper.load_model(AppConfig.label, model_name)
    except ImproperlyConfigured:
        # fall back to the old label while things are still registered there
        return swapper.load_model('openwisp_notifications', model_name)