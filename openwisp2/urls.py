from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path, reverse_lazy
from django.views.generic import RedirectView
# from django.views.generic import TemplateView 
# from nexappvpn.wizards import TunnelCreationWizard,FORMS

# from nexappvpn.forms import TunnelStep1Form, TunnelStep2Form, TunnelStep3Form
from django.contrib.admin.views.decorators import staff_member_required

redirect_view = RedirectView.as_view(url=reverse_lazy('admin:index'))

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('openwisp_controller.urls')),
    path('api/v1/', include('openwisp_utils.api.urls')),
    path('api/v1/', include('openwisp_users.api.urls')),
    path('/', include('openwisp_network_topology.urls')),
    path('', include('openwisp_monitoring.urls')),
    path('', include('openwisp_radius.urls')),
       # path('api/sdwan_tunnel/', include('sdwan_tunnel.urls')),
    path('', redirect_view, name='index'),
    path('vpn/ipsec/', include('vpn_ipsec.urls')),
    path('sdwan/', include('sdwan_tunnel.api.urls')),
   
]


urlpatterns += staticfiles_urlpatterns()
