from django.urls import path
from . import views
 
urlpatterns = [
     path('', views.config_form, name='config_form'),  # default view for vpn/ipsec/

    path('get-config/', views.get_config, name='get_config'),
    path('set-config/', views.set_config, name='set_config'),
]