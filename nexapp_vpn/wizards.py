 
from django.shortcuts import redirect, render
from formtools.wizard.views import SessionWizardView
from .models import Tunnel
from .forms import TunnelStep1Form, TunnelStep2Form, TunnelStep3Form
from django.contrib import messages
 
FORMS = [
    ("step1", TunnelStep1Form),
    ("step2", TunnelStep2Form),
    ("step3", TunnelStep3Form),
]
 
TEMPLATES = {
    "step1": "vpn_wizard/step1.html",
    "step2": "vpn_wizard/step2.html",
    "step3": "vpn_wizard/step3.html",
}

class TunnelCreationWizard(SessionWizardView):
    form_list = dict(FORMS)

    def get_template_names(self):
        return [TEMPLATES[self.steps.current]]

    def done(self, form_list, **kwargs):
        data = {}
        for form in form_list:
            data.update(form.cleaned_data)

        try:
            tunnel = Tunnel.objects.create(
                organization=self.request.user.organizationuser.organization,
                name=data.get('name'),
                vpn_type=data.get('vpn_type'),
                mode=data.get('mode'),
                hub1_public_ip=data.get('hub1_public_ip'),
                spoke_public_ip=data.get('spoke_public_ip'),
                hub1_lan_subnet=data.get('hub1_lan_subnet'),
                spoke_lan_subnet=data.get('spoke_lan_subnet'),
                ike_proposal=data.get('ike_proposal'),
                esp_proposal=data.get('esp_proposal'),
                auto_psk=data.get('auto_psk'),
                device_a=data.get('device_a'),
                created_by=self.request.user.organizationuser,
            )

            if 'device_b' in data:
                tunnel.device_b.set(data['device_b'])

            tunnel.save()

            result = tunnel.push_to_agent()
            messages.add_message(
                self.request,
                messages.SUCCESS if result['status'] == 'success' else messages.ERROR,
                result['message']
            )
            return redirect("admin:vpn_tunnel_change", tunnel.id)

        except Exception as e:
            messages.error(self.request, f"An error occurred: {e}")
            return redirect("admin:vpn_tunnel_changelist")
