from django import forms
from sdwan_tunnel.models.tunnel import Tunnel
from openwisp_controller.config.models import Config as Device
from sdwan_tunnel.protocols.ipsec.client import fetch_online_devices_by_names
from sdwan_tunnel.models.pathlabel import PathLabel
from sdwan_tunnel.models.qos import QOSPolicy
from sdwan_tunnel.widgets import ColorPaletteWidget ,ToggleSwitchWidget
# from .widgets import ToggleSwitchWidget, ColorPaletteWidget
from openwisp_controller.config.models import Device as OwDevice
from django.forms import inlineformset_factory
from django.utils.html import escape
import json
from django.core.exceptions import ValidationError
from openwisp_controller.config.models import Config as Device
from sdwan_tunnel.models.fullmesh import FullMesh
from openwisp_controller.config.models import Config as ConfigModel, Device as OwDevice

class TunnelForm(forms.ModelForm):
    class Meta:
        model = Tunnel
        fields = '__all__'
 
    


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    # def __init__(self, *args, kwargs): 
    #     super().__init__(args, **kwargs)
        
 
        # 1. Get all device names
        all_names = Device.objects.values_list('name', flat=True)
 
        # 2. Fetch online device names from OpenWISP Agent
        online = fetch_online_devices_by_names(list(all_names))
        online_names = [d['name'] for d in online]
 
        # 3. Filter device_a and device_b queryset to online devices
        self.fields['device_a'].queryset = Device.objects.filter(name__in=online_names)
 
        # ✅ Fix typo: namein → namein
        self.fields['device_b'].queryset = Device.objects.filter(name__in=online_names)
 
        # 4. If Device A is selected, exclude it from Device B choices
        if 'device_a' in self.data:
            try:
                selected_id = int(self.data['device_a'])
                self.fields['device_b'].queryset = self.fields['device_b'].queryset.exclude(id=selected_id)
            except (ValueError, TypeError):
                pass





class PathLabelForm(forms.ModelForm):
    class Meta:
        model = PathLabel
        fields = '__all__'
        widgets = {
            'color': ColorPaletteWidget(attrs={'style': 'width:100px;'}),
            # 'direct_internet_access': ToggleSwitchWidget(),
        }


class QOSPolicyForm(forms.ModelForm):
    class Meta:
        model = QOSPolicy
        fields = '__all__'
        widgets = {

            'realtime_bandwidth_limit': forms.NumberInput(attrs={'type': 'range', 'min': 10, 'max': 70, 'step': 10}),
            'control_signaling_weight': forms.NumberInput(attrs={'type': 'range', 'min': 10, 'max': 70, 'step': 10}),
            'prime_select_weight': forms.NumberInput(attrs={'type': 'range', 'min': 10, 'max': 70, 'step': 10}),
            'standard_select_weight': forms.NumberInput(attrs={'type': 'range', 'min': 10, 'max': 70, 'step': 10}),
            'best_effort_weight': forms.NumberInput(attrs={'type': 'range', 'min': 10, 'max': 70, 'step': 10}),
            'high_bandwidth_limit': forms.NumberInput(attrs={'type': 'range', 'min': 0, 'max': 100, 'step': 1}),
            'medium_bandwidth_limit': forms.NumberInput(attrs={'type': 'range', 'min': 0, 'max': 100, 'step': 1}),
            'low_bandwidth_limit': forms.NumberInput(attrs={'type': 'range', 'min': 0, 'max': 100, 'step': 1}),
        }


class MembersTableWidget(forms.Widget):
    
    def render(self, name, value, attrs=None, renderer=None):
        import json
        from django.utils.html import escape

        value = value or []
        try:
            rows = json.loads(value) if isinstance(value, str) else value
        except Exception:
            rows = []



        # ✅ merge widget-level attrs and call-time attrs
        merged_attrs = {}
        if getattr(self, 'attrs', None):
            merged_attrs.update(self.attrs)
        if attrs:
            merged_attrs.update(attrs)

        device_choices = merged_attrs.get('device_choices', [])  # [(pk, label), ...]

        # ✅ ensure at least one row on a fresh form
        if not rows:
            rows = [{}]

        def global_options_html():
            opts = ['<option value="">Select device</option>']
            for v, label in device_choices:
                opts.append(f'<option value="{escape(str(v))}">{escape(str(label))}</option>')
            return ''.join(opts)

        all_opts_html = global_options_html()

        def row_options_html(selected):
            opts = ['<option value="">Select device</option>']
            for v, label in device_choices:
                sel = ' selected' if str(v) == str(selected or '') else ''
                opts.append(f'<option value="{escape(str(v))}"{sel}>{escape(str(label))}</option>')
            return ''.join(opts)

        trs = []
        for i, r in enumerate(rows):
            device_val = r.get('device') or ''
            subnet = r.get('subnet') or ''
            local_ip = r.get('local_ip') or ''
            wan_ip = r.get('wan_ip') or ''
            uuid = r.get('uuid') or ''
            is_enabled = 'checked' if r.get('is_enabled', True) else ''
            trs.append(f"""
              <tr data-index="{i}">
                <td>
                  <select class="form-select fm-device">
                    {row_options_html(device_val)}
                  </select>
                </td>
                <td><input type="text" class="form-control fm-subnet" value="{escape(subnet)}"></td>
                <td><input type="text" class="form-control fm-local" value="{escape(local_ip)}"></td>
                <td><input type="text" class="form-control fm-wan" value="{escape(wan_ip)}"></td>
                <td><input type="text" class="form-control fm-uuid" value="{escape(uuid)}"></td>
                <td class="text-center"><input type="checkbox" class="form-check-input fm-enabled" {is_enabled}></td>
                <td><button type="button" class="btn btn-outline-danger btn-sm fm-remove">×</button></td>
              </tr>
            """)

        html = f"""
<div class="fm-wrap" data-options-html='{json.dumps(all_opts_html)}'>
  <input type="hidden" name="{name}" id="id_{name}" value='{json.dumps(rows)}'>
  <div class="table-responsive">
    <table class="table table-sm table-striped align-middle">
      <thead class="table-light">
        <tr>
          <th style="width:25%">Device</th>
          <th>Subnet</th>
          <th>Local IP</th>
          <th>WAN IP</th>
          <th>UUID</th>
          <th>Enabled</th>
          <th style="width:1%"></th>
        </tr>
      </thead>
      <tbody class="fm-rows">
        {''.join(trs)}
      </tbody>
    </table>
  </div>
  <button type="button" class="btn btn-outline-primary btn-sm fm-add">+ Add device</button>
</div>
<script>
(function(){{
  const wrap = document.currentScript.previousElementSibling;
  const input = wrap.querySelector('input[type=hidden]');
  const tbody = wrap.querySelector('.fm-rows');
  const addBtn = wrap.querySelector('.fm-add');
  const optionsHTML = JSON.parse(wrap.dataset.optionsHtml);

  function serialize() {{
    const rows = [];
    tbody.querySelectorAll('tr').forEach(tr => {{
      rows.push({{
        device: tr.querySelector('.fm-device').value || null,
        subnet: tr.querySelector('.fm-subnet').value || null,
        local_ip: tr.querySelector('.fm-local').value || null,
        wan_ip: tr.querySelector('.fm-wan').value || null,
        uuid: tr.querySelector('.fm-uuid').value || null,
        is_enabled: tr.querySelector('.fm-enabled').checked
      }});
    }});
    input.value = JSON.stringify(rows);
  }}

  function makeRow() {{
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><select class="form-select fm-device">${{optionsHTML}}</select></td>
      <td><input type="text" class="form-control fm-subnet" placeholder="10.10.x.0/24"></td>
      <td><input type="text" class="form-control fm-local" placeholder="Mgmt IP"></td>
      <td><input type="text" class="form-control fm-wan" placeholder="Public/WAN IP"></td>
      <td><input type="text" class="form-control fm-uuid" placeholder="Optional external UUID"></td>
      <td class="text-center"><input type="checkbox" class="form-check-input fm-enabled" checked></td>
      <td><button type="button" class="btn btn-outline-danger btn-sm fm-remove">×</button></td>
    `;
    return tr;
  }}

  addBtn.addEventListener('click', () => {{
    const tr = makeRow();
    tbody.appendChild(tr);
    serialize();
  }});
  tbody.addEventListener('input', serialize);
  tbody.addEventListener('change', serialize);
  tbody.addEventListener('click', (e) => {{
    if (e.target.classList.contains('fm-remove')) {{
      e.target.closest('tr').remove();
      serialize();
    }}
  }});

  // initial serialize
  serialize();
}})();
</script>
        """
        return html


class MembersTableField(forms.Field):
    widget = MembersTableWidget
    def to_python(self, value):
        if value in (None, '', []):
            return []
        if isinstance(value, list):
            return value
        try:
            return json.loads(value)
        except Exception as e:
            raise ValidationError("Invalid members JSON") from e


class FullMeshForm(forms.ModelForm):
    members = MembersTableField(required=False)

    class Meta:
        model = FullMesh
        fields = [
            'name', 'description', 'is_enabled',
            'members',
            'ike_version','ike_encryption_algorithm','ike_integrity_algorithm',
            'ike_diffie_hellman_group','ike_key_lifetime',
            'esp_version','esp_encryption_algorithm','esp_integrity_algorithm',
            'esp_diffie_hellman_group','esp_key_lifetime',
            'dpdaction','ipcomp','pre_shared_key',
        ]
        widgets = {'description': forms.Textarea(attrs={'rows': 2})}

    

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        cfg_qs = ConfigModel.objects.select_related('device')
        cfg_choices = [(obj.pk, getattr(obj.device, 'name', str(obj))) for obj in cfg_qs]

        if cfg_choices:
            choices = cfg_choices
            self.fields['members'].widget.attrs['device_pk_kind'] = 'config'
        else:
            dev_choices = list(OwDevice.objects.order_by('name').values_list('pk', 'name'))
            choices = dev_choices
            self.fields['members'].widget.attrs['device_pk_kind'] = 'device'

        # ✅ set choices once; do NOT override later
        self.fields['members'].widget.attrs['device_choices'] = choices

        # (Optional) quick debug in admin to confirm it loaded
        self.fields['members'].help_text = f"Devices loaded: {len(choices)}"
        
        

