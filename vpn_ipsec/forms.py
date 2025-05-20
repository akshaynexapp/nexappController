# #vpn_ipsec/forms.py
from django import forms
 
class IPSecConfigForm(forms.Form):
    service = forms.ChoiceField(choices=[('enable', 'Enable'), ('disable', 'Disable')])
    remote_mg_ip = forms.CharField(max_length=32)
    remote_subnet = forms.CharField(max_length=32)
    remote_wan_ip = forms.CharField(max_length=32)
    local_mg_ip = forms.CharField(max_length=32)
    local_wan_ip = forms.CharField(max_length=32)
    local_subnet = forms.CharField(max_length=32)