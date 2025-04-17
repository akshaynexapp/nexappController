from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path, reverse_lazy
from django.views.generic import RedirectView
# from django.views.generic import TemplateView 


redirect_view = RedirectView.as_view(url=reverse_lazy('admin:index'))

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('openwisp_controller.urls')),
    path('api/v1/', include('openwisp_utils.api.urls')),
    path('api/v1/', include('openwisp_users.api.urls')),
    path('/', include('openwisp_network_topology.urls')),
    path('', include('openwisp_monitoring.urls')),
    path('', include('openwisp_radius.urls')),
    # path('api/vpn/', include('nexapp_vpn.urls')),
    path('nexappdevices/data/', include('nexappdevice.urls')),
    path('', redirect_view, name='index'),
    # path('vpn/', TemplateView.as_view(template_name='index.html')),

]

urlpatterns += staticfiles_urlpatterns()
