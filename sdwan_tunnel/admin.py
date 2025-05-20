from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db import models
from django.forms import TextInput, Textarea, Select, NumberInput
from django.urls import path
from .tasks import push_tunnel_async
from django.contrib import messages
from django.shortcuts import redirect
from django import forms

from sdwan_tunnel.models import (
    Tunnel,
    DevicePeer,
    ConfigHistory,
    TunnelStatus,
    AuditLogEntry
)



@admin.register(Tunnel)
class TunnelAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'vpn_type', 'mode', 'status', 'organization',
        'is_enabled', 'last_pushed_at', 'push_button', 'rollback_button'
    )
    list_filter = ('vpn_type', 'mode', 'status', 'organization', 'is_enabled')
    search_fields = ('name', 'organization_name', 'local_identifier', 'remote_identifier')
    readonly_fields = ('last_config_hash', 'last_pushed_at','pre_shared_key','subnet'
                       )
    fieldsets = (
       
        (None, {
            'fields': (
                'organization', 'name', 'vpn_type', 'mode', 'status',
                'is_enabled', 'local_identifier', 'remote_identifier',
                'device_a','device_a_wan_ip','device_a_subnet','device_b','device_b_wan_ip','device_b_subnet'
                ,'last_pushed_at','last_config_hash','pre_shared_key','subnet',  'dpdaction',
        'ipcomp',
                
                
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
        models.CharField:       {'widget': forms.TextInput(attrs={'style': 'width:300px;'})},
        models.TextField:       {'widget': forms.Textarea(attrs={'style': 'width:300px;'})},
        models.ForeignKey:      {'widget': forms.Select(attrs={'style': 'width:300px;'})},
        models.PositiveIntegerField: {'widget': forms.NumberInput(attrs={'style': 'width:300px;'})},
        # Explicitly map BooleanField → CheckboxInput **without** styling
        models.BooleanField:    {'widget': forms.CheckboxInput(attrs={'style': 'width:100px;'})},
    }
    

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
        # if obj.last_pushed_at:
        #     # already pushed once → show a Modify link to the change‐form
        #     return format_html(
        #         '<a class="button" href="./{pk}/change/" '
        #         'style="opacity:0.5;pointer-events:none;">Modify</a>',
        #         pk=obj.pk
        #     )
        # else:
        #     # never pushed → show the Push action
        #     return format_html(
        #         '<a class="button" href="./{pk}/push/">Push</a>',
        #         pk=obj.pk
        #     )


    push_button.short_description = 'Action'
    # push_button.allow_tags = True

    # push_button.short_description = 'Push'

    
    




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
 
    

@admin.register(DevicePeer)
class DevicePeerAdmin(admin.ModelAdmin):
    list_display = ('tunnel', 'local_device', 'peer_device', 'local_role', 'peer_role', 'link_subnet')
    list_filter = ('local_role', 'peer_role')
    search_fields = ('tunnel__name', 'local_device__name', 'peer_device__name')
 
@admin.register(ConfigHistory)
class ConfigHistoryAdmin(admin.ModelAdmin):
    list_display = ('tunnel', 'action',  'created_at')
    # list_filter = ('action',)
    readonly_fields = ('payload', 'config_hash', 'created_at')
 
@admin.register(TunnelStatus)
class TunnelStatusAdmin(admin.ModelAdmin):
    list_display = ('tunnel', 'is_up', 'latency_ms', 'jitter_ms', 'packet_loss_percent', 'timestamp')
    list_filter = ('is_up',)
    readonly_fields = ('timestamp',)
 
@admin.register(AuditLogEntry)
class AuditLogEntryAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'topology_id', 'timestamp')
    search_fields = ('event', 'userusername')
    readonly_fields = ('devices', 'details', 'timestamp')