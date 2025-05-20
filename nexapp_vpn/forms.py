
from django import forms
from .models import Device, Tunnel



class TunnelStep1Form(forms.Form):
    name = forms.CharField(label='Tunnel Name')
    vpn_type = forms.ChoiceField(choices=Tunnel._meta.get_field('vpn_type').choices)
    mode = forms.ChoiceField(choices=Tunnel._meta.get_field('mode').choices)
    device_a = forms.ModelChoiceField(queryset=Device.objects.filter(status='Online'))
    device_b = forms.ModelMultipleChoiceField(queryset=Device.objects.filter(status='Online'))
 
class TunnelStep2Form(forms.Form):
    hub1_public_ip = forms.GenericIPAddressField()
    spoke_public_ip = forms.GenericIPAddressField()
    hub1_lan_subnet = forms.CharField()
    spoke_lan_subnet = forms.CharField()
 
class TunnelStep3Form(forms.Form):
    ike_proposal = forms.CharField(initial='aes256-sha256-modp2048')
    esp_proposal = forms.CharField(initial='aes256-sha256')
    auto_psk = forms.CharField(initial='', required=False)
 
    def clean_auto_psk(self):
        value = self.cleaned_data.get('auto_psk')
        if not value:
            import secrets
            return secrets.token_hex(32)
        return value
    

 
class TunnelConfigForm(forms.Form):
    service = forms.ChoiceField(choices=[('enable', 'Enable'), ('disable', 'Disable')])
    remote_mg_ip = forms.CharField(max_length=32)
    remote_subnet = forms.CharField(max_length=32)
    remote_wan_ip = forms.CharField(max_length=32)
    local_mg_ip = forms.CharField(max_length=32)
    local_wan_ip = forms.CharField(max_length=32)
    local_subnet = forms.CharField(max_length=32)