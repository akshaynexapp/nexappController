
 
from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
from .models import Tunnel, TunnelStatusLog, TunnelConfigHistory, TunnelHealthMetric, DevicePeer , fetch_management_ips_by_names
from django import forms
from django.db import models
from django.forms import TextInput, Textarea, Select,NumberInput
from .tasks import push_tunnel_async
from django.conf import settings
import requests

@admin.register(Tunnel)
class TunnelAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'vpn_type', 'mode', 'status', 'organization',
        'is_enabled', 'last_pushed_at', 'push_button', 'rollback_button'
    )
    list_filter = ('vpn_type', 'mode', 'status', 'organization', 'is_enabled')
    search_fields = ('name', 'organization__name', 'local_identifier', 'remote_identifier')
    readonly_fields = ('last_config_hash', 'last_pushed_at')
    actions = ['delete_selected_tunnels']

    fieldsets = (
       
        (None, {
            'fields': (
                'organization', 'name', 'vpn_type', 'mode', 'template', 'status',
                'is_enabled', 'local_identifier', 'remote_identifier',
                'device_a','device_b','last_pushed_at','last_config_hash'
                
            )
        }),
        ('IKE Phase 1 Parameters', {
            
            'fields': (
                'ike_version', 'ike_encryption_algorithm', 'ike_integrity_algorithm',
                'ike_diffie_hellman_group', 'ike_key_lifetime'
            ),
        }),
        ('ESP Phase 2 Parameters', {
            
            'fields': (
                'esp_version', 'esp_encryption_algorithm', 'esp_integrity_algorithm',
                'esp_diffie_hellman_group', 'esp_key_lifetime'
            ),
        }),
       
    )
    formfield_overrides = {
        # text inputs
        models.CharField: {
            'widget': TextInput(attrs={'style': 'width:300px;'}),
        },
        # long text areas
        models.TextField: {
            'widget': Textarea(attrs={'style': 'width:300px;'}),
        },
        # foreign-key dropdowns
        models.ForeignKey: {
            'widget': Select(attrs={'style': 'width:300px;'}),
        },
        # numeric fields (like your key lifetimes)
        models.PositiveIntegerField: {
            'widget': NumberInput(attrs={'style': 'width:300px;'}),
        },
    }

    def formfield_for_dbfield(self, db_field, **kwargs):
        """
        Catch‐all: whatever widget Django picks (Select for choices, NumberInput,
        DateTimeInput, etc.), give it a 300px width if it has attrs.
        """
        formfield = super().formfield_for_dbfield(db_field, **kwargs)
        if formfield and hasattr(formfield.widget, 'attrs'):
            formfield.widget.attrs.update({'style': 'width:300px;'})
        return formfield
     
    def get_urls(self):
      urls = super().get_urls()
      custom = [
          path('<int:tunnel_id>/push/',
               self.admin_site.admin_view(self.process_push),
               name='vpn_tunnel_push'),
          path('<int:tunnel_id>/rollback/',
               self.admin_site.admin_view(self.process_rollback),
               name='vpn_tunnel_rollback'),
      ]
      return custom + urls
 
    def push_button(self, obj):
        return format_html('<a class="button" href="{}">Push</a>',
                           f'./{obj.pk}/push/')
    push_button.short_description = 'Push'
    def rollback_button(self, obj):
        return format_html('<a class="button" href="{}">Rollback</a>',
                           f'./{obj.pk}/rollback/')
    rollback_button.short_description = 'Rollback'
 
    def process_push(self, request, tunnel_id):
        # enqueue the Celery task
        push_tunnel_async.delay(tunnel_id)
        self.message_user(
            request,
            "Push scheduled in background. Check logs for status.",
            messages.INFO
        )
        return redirect(request.META.get('HTTP_REFERER', '../'))
 
   
 
    def process_rollback(self, request, tunnel_id):
        tunnel = Tunnel.objects.get(pk=tunnel_id)
        result = tunnel.rollback_last_config()
        self.message_user(request, result['message'], messages.SUCCESS if result['status'] == 'success' else messages.ERROR)
        return redirect(request.META.get('HTTP_REFERER'))
 
    # … your fieldsets, formfield_overrides, get_urls, push/rollback buttons …  
 

    def _get_related_device_names(self, tunnel):
        """
        Return device.name list based on tunnel.mode:
         - site_to_site → [device_a, device_b]
         - hub_spoke    → [device_a] + all spokes in device_b
         - full_mesh    → [device_a] + all peers in device_b
        """
        if tunnel.mode == 'site_to_site':
            return [tunnel.device_a.name, tunnel.device_b.name]
        if tunnel.mode == 'hub_spoke':
            return [tunnel.device_a.name] + [d.name for d in tunnel.device_b.all()]
        if tunnel.mode == 'full_mesh':
            return [tunnel.device_a.name] + [d.name for d in tunnel.device_b.all()]
        # fallback
        return [tunnel.device_a.name, tunnel.device_b.name]
 
    def _delete_on_device(self, mg_ip: str, tunnel_name: str):
        """
        1) POST get-config to list tunnels
        2) match by name → get id
        3) POST delete-tunnel with that id
        """
        url = f"https://{mg_ip}/api-new/ipsec"
        # fetch config
        resp = requests.post(
            url,
            json={"method": "get-config", "payload": {}},
            timeout=10,
            verify=False
        )
        resp.raise_for_status()
        tunnels = resp.json().get("data", {}).get("tunnels", [])
        match = next((t for t in tunnels if t.get("name") == tunnel_name), None)
        if not match:
            raise RuntimeError(f"Tunnel '{tunnel_name}' not found on {mg_ip}")
        # delete it
        dr = requests.post(
            url,
            json={"method": "delete-tunnel", "payload": {"id": match["id"]}},
            timeout=10,
            verify=False
        )
        dr.raise_for_status()
 
    def delete_model(self, request, obj):
        """
        Override single-object delete: call remote deletes first, then local delete.
        """
        name = obj.name
        # 1) figure out which devices to hit
        device_names = self._get_related_device_names(obj)
        # 2) resolve mgmt IPs
        ips = fetch_management_ips_by_names(device_names)
        missing = [n for n in device_names if n not in ips]
        if missing:
            self.message_user(
                request,
                f"❌ Could not resolve IPs for: {', '.join(missing)}",
                level=messages.ERROR
            )
            return
        # 3) perform remote deletes
        try:
            for dn in device_names:
                self._delete_on_device(ips[dn], name)
        except Exception as e:
            self.message_user(
                request,
                f"❌ Remote delete failed for '{name}': {e}",
                level=messages.ERROR
            )
            return
        # 4) if all succeeded, delete locally
        super().delete_model(request, obj)
        self.message_user(
            request,
            f"✅ Tunnel '{name}' removed from {', '.join(device_names)} and deleted locally.",
            level=messages.SUCCESS
        )
 
    def delete_queryset(self, request, queryset):
        """
        Override bulk delete: iterate each Tunnel, remote-delete on related devices,
        then clean up only the ones that succeeded.
        """
        # 1) collect all needed device names
        all_names = set()
        tunnel_map = {}
        for t in queryset:
            devs = self._get_related_device_names(t)
            tunnel_map[t] = devs
            all_names.update(devs)
        # 2) resolve IPs in one go
        ips = fetch_management_ips_by_names(list(all_names))
 
        successes = []
        for tunnel, dev_names in tunnel_map.items():
            missing = [n for n in dev_names if n not in ips]
            if missing:
                self.message_user(
                    request,
                    f"❌ '{tunnel.name}': missing IPs for {', '.join(missing)}",
                    level=messages.ERROR
                )
                continue
            try:
                for dn in dev_names:
                    self._delete_on_device(ips[dn], tunnel.name)
                successes.append(tunnel)
            except Exception as e:
                self.message_user(
                    request,
                    f"❌ '{tunnel.name}': remote delete failed ({e})",
                    level=messages.ERROR
                )
        # 3) locally delete only successful tunnels
        if successes:
            super().delete_queryset(request, successes)
            self.message_user(
                request,
                f"✅ Deleted {len(successes)} tunnels locally after remote deletions.",
                level=messages.SUCCESS
            )


admin.site.register(TunnelStatusLog)
admin.site.register(TunnelConfigHistory)
admin.site.register(TunnelHealthMetric)
admin.site.register(DevicePeer)


