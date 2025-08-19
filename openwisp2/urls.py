from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path, reverse_lazy
from django.views.generic import RedirectView
# from django.views.generic import TemplateView 
# from nexappvpn.wizards import TunnelCreationWizard,FORMS

# from nexappvpn.forms import TunnelStep1Form, TunnelStep2Form, TunnelStep3Form
from django.contrib.admin.views.decorators import staff_member_required
from controller_reports.views import reports_dashboard_admin_view
from controller_reports.views import admin_report_slug_view

redirect_view = RedirectView.as_view(url=reverse_lazy('admin:index'))

urlpatterns = [
    path("admin/reports/all/",
         admin.site.admin_view(reports_dashboard_admin_view),
         name="admin_reports_all"),
    path("admin/reports/<slug:slug>/",
     admin.site.admin_view(admin_report_slug_view),
     name="admin_report_slug"),
    path('admin/', admin.site.urls),
    path('', include('openwisp_controller.urls')),
    path('api/v1/', include('openwisp_utils.api.urls')),
    path('api/v1/', include('openwisp_users.api.urls')),
    path('/', include('openwisp_network_topology.urls')),
    path('', include('openwisp_monitoring.urls')),
    path('', include('openwisp_radius.urls')),
    path('firmware/', include('openwisp_firmware_upgrader.urls')),
    path('', redirect_view, name='index'),
    path('vpn/ipsec/', include('vpn_ipsec.urls')),
    path('api/v1/', include('sdwan_tunnel.api.urls')),
    path('api/v1/', include('traffic_application.api.urls')),
    path('reports/', include('controller_reports.urls')),
    path('accounts/', include('openwisp_users.accounts.urls')),
]


urlpatterns += staticfiles_urlpatterns()
