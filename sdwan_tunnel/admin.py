from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db import models
from openwisp_controller.config.models import Config as Device
from .api_client import delete_tunnel_by_name, TunnelAPIError
from openwisp_users.models import OrganizationUser
from sdwan_tunnel.forms import TunnelForm , PathLabelForm , QOSPolicyForm,FullMeshForm
from django.utils.safestring import mark_safe

from django.forms import TextInput, Textarea, Select, NumberInput
from django.urls import path
from .tasks import push_tunnel_async
from .tasks import push_hub_spoke_tunnel_async
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.shortcuts import redirect
from django import forms
from sdwan_tunnel.models import (
    Tunnel,
    Hub,
    ConfigHistory,
    AuditLogEntry,
    Spoke, 
    Job
    
)
from django.shortcuts import render, get_object_or_404
from sdwan_tunnel.models.pathlabel import PathLabel
from sdwan_tunnel.models.sdwanzone import SDWANZone
from sdwan_tunnel.models.firewall import Firewall
from sdwan_tunnel.models.qos import QOSPolicy
from sdwan_tunnel.models.fullmesh import FullMesh
from sdwan_tunnel.models.linkmonitoring import LinkMonitoring


@admin.register(Tunnel)
class TunnelAdmin(admin.ModelAdmin):
    # form = TunnelForm
    list_display = (
        'name', 'vpn_type', 'status', 'latency','jitter','packet_loss',
         'last_pushed_at', 'last_push_message', 'push_button', 'rollback_button'
    )
    list_filter = ('vpn_type', 'mode',  'organization', 'is_enabled')
    search_fields = ('name', 'organization_name')
    readonly_fields = ('last_config_hash', 'created_by', 'organization','last_pushed_at','status','created_at','pre_shared_key','packet_loss','last_push_message',
                       'uuid_b','uuid_a','jitter','latency' ,'local_ip_b','local_ip_a','updated_at','last_config_payload'
                       )
    fieldsets = (
       
        (None, {
            'fields': (
                'organization', 'name', 'vpn_type', 'mode', 'status',
                'is_enabled', 'created_by',
                'device_a','device_a_wan_ip','device_a_subnet','device_b','device_b_wan_ip','device_b_subnet', 
                'latency', 'jitter' ,'packet_loss','dpdaction',
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

        ('Status & Timestamps',
            {
                'fields': [
                   'uuid_a', 'uuid_b', 'local_ip_b','local_ip_a',
                    'last_pushed_at','last_config_hash','pre_shared_key','created_at',  'updated_at',
                'last_config_payload',
                ],
                'classes': ['collapse'],
            }
        ),
       
    )
    formfield_overrides = {
        models.CharField:       {'widget': forms.TextInput(attrs={'style': 'width:300px;'})},
        models.TextField:       {'widget': forms.Textarea(attrs={'style': 'width:300px;'})},
        models.ForeignKey:      {'widget': forms.Select(attrs={'style': 'width:300px;'})},
        models.PositiveIntegerField: {'widget': forms.NumberInput(attrs={'style': 'width:300px;'})},
        # Explicitly map BooleanField → CheckboxInput **without** styling
        models.BooleanField:    {'widget': forms.CheckboxInput(attrs={'style': 'width:100px;'})},
    }

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # only on create
            obj.created_by = request.user

            # Assign first organization of this user
            org_user = OrganizationUser.objects.filter(user=request.user).first()
            if org_user:
                obj.organization = org_user.organization

        super().save_model(request, obj, form, change)
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        # 1) gather all devices used by hubs or spokes
        hub_ids   = set(Hub.objects.values_list('local_device_id', flat=True))
        spoke_ids = set(Spoke.objects.values_list('device_id',     flat=True))
        # 2) gather all devices already assigned in any Tunnel
        used_in_tunnels_a = set(Tunnel.objects.values_list('device_a_id', flat=True))
        used_in_tunnels_b = set(Tunnel.objects.values_list('device_b_id', flat=True))

        used = hub_ids | spoke_ids | used_in_tunnels_a | used_in_tunnels_b

        # 3) when editing an existing Tunnel, allow its own devices
        if obj:
            if obj.device_a_id:
                used.discard(obj.device_a_id)
            if obj.device_b_id:
                used.discard(obj.device_b_id)

        # 4) override picklists
        qs = Device.objects.exclude(pk__in=used)
        form.base_fields['device_a'].queryset = qs
        form.base_fields['device_b'].queryset = qs

        return form

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # if you're rendering raw_id_fields or want to guard any FK
        if db_field.name in ('device_a', 'device_b'):
            hub_ids   = set(Hub.objects.values_list('local_device_id', flat=True))
            spoke_ids = set(Spoke.objects.values_list('device_id',      flat=True))
            used_in_tunnels_a = set(Tunnel.objects.values_list('device_a_id', flat=True))
            used_in_tunnels_b = set(Tunnel.objects.values_list('device_b_id', flat=True))

            used = hub_ids | spoke_ids | used_in_tunnels_a | used_in_tunnels_b

            # allow the current tunnel’s devices
            object_id = request.resolver_match.kwargs.get('object_id')
            if object_id:
                tunnel = Tunnel.objects.filter(pk=object_id).first()
                if tunnel:
                    if tunnel.device_a_id:
                        used.discard(tunnel.device_a_id)
                    if tunnel.device_b_id:
                        used.discard(tunnel.device_b_id)

            kwargs['queryset'] = Device.objects.exclude(pk__in=used)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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
       

    push_button.short_description = 'Action'
  

    def rollback_button(self, obj):
        return format_html('<a class="button" href="{}">Rollback</a>',
                           f'./{obj.pk}/rollback/')
    rollback_button.short_description = 'Rollback'
    

    def last_push_message(self, obj):
        return obj.last_push_message or "—"

    last_push_message.short_description = "Message"


    def process_push(self, request, tunnel_id):
        # enqueue the Celery task
        tunnel = Tunnel.objects.get(pk=tunnel_id)
        job = Job.objects.create(
            tunnel=tunnel,
            triggered_by=request.user,
            status="pending",
            message="Push scheduled"
    )
        tunnel.last_push_message ="Push sheduled"
        tunnel.save(update_fields=["last_push_message"])
        push_tunnel_async.delay(tunnel_id, job.id)

        
        self.message_user(
            request,
            "Push scheduled in background. Check logs for status.",
            messages.INFO
        )
        return redirect(request.META.get('HTTP_REFERER', '../'))
 
        # tunnel = Tunnel.objects.get(pk=tunnel_id)

        # result = tunnel.push_to_agent(full_replace=False)
    

        # status = result.get("status", "error")
        # msg    = result.get("message", "No message returned")
        # level  = messages.SUCCESS if status == "success" else messages.ERROR
        # self.message_user(request, msg, level)
    
        # # 5. Go back to the changelist or wherever you came from
        # return redirect(request.META.get('HTTP_REFERER', '../'))


 
    def process_rollback(self, request, tunnel_id):
        tunnel = Tunnel.objects.get(pk=tunnel_id)
        result = tunnel.rollback_last_config()
        self.message_user(request, result['message'], messages.SUCCESS if result['status'] == 'success' else messages.ERROR)
        return redirect(request.META.get('HTTP_REFERER'))
 
    def delete_model(self, request, obj):
        self._delete_remote_tunnel(obj, request)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for tunnel in queryset:
            self._delete_remote_tunnel(tunnel, request)
        super().delete_queryset(request, queryset)

    def _delete_remote_tunnel(self, obj, request=None):
        """
        Internal helper to delete the tunnel from both devices.
        """
        errors = []

        for ip in [obj.local_ip_a, obj.local_ip_b]:
            try:
                delete_tunnel_by_name(obj.name, ip)
            except TunnelAPIError as e:
                msg = f"{obj.name}@{ip}: {e}"
                errors.append(msg)
                if request:
                    from django.contrib import messages
                    self.message_user(request, msg, level=messages.WARNING)

        return errors

@admin.register(ConfigHistory)
class ConfigHistoryAdmin(admin.ModelAdmin):
    list_display = ('tunnel', 'action',  'created_at')
    # list_filter = ('action',)
    readonly_fields = ('payload', 'config_hash', 'created_at')
 
@admin.register(AuditLogEntry)
class AuditLogEntryAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'topology_id', 'timestamp')
    search_fields = ('event', 'userusername')
    readonly_fields = ('devices', 'details', 'timestamp')


@admin.register(Spoke)
class SpokeAdmin(admin.ModelAdmin):
    list_display    = ('device', 'hub_device',  'status','up_time','latency', 'jitter', 'packet_loss','display_path_labels', 'last_pushed_at','last_push_message','push_button')
    list_filter = ('status', 'is_enabled', 'link_monitor',"up_time",'domain_monitor','path_labels')
    search_fields   = ('device', 'hub_device', 'status')
    readonly_fields = ('status', 'up_time', 'organization', 'local_ip', 'created_at','created_by',  'last_push_message','last_pushed_at', 'updated_at','latency', 'jitter', 'packet_loss','uuid')

    fieldsets = [
        # Section 1: Core relations
        (
            None,
            {
                'fields': [
                    'device',
                    'hub_device',
                    'created_by',
                    'organization',
                ]
            }
        ),
        # Section 2: Networking
        (
            'Networking',
            {
                'fields': [
                    'local_ip',
                    'wan_ip',
                    'subnet',
                    'is_enabled',
                    'latency',
                    'jitter',
                    'packet_loss',
                    'up_time',
                ]
            }
        ),
        # Section 3: Status & timestamps
        #  ('Monitoring', {'fields': ['link_monitor'],
        #                  'classes': ['collapse'],}),
        ('Monitoring', {'fields': ['link_monitor', 'domain_monitor'],
                        'classes': ['collapse'],}),
        (None, {'fields': ['path_labels']}),
        (
            'Status & Timestamps',
            {
                'fields': [
                    'uuid',
                    'status',
                    'last_pushed_at',
                    'created_at',
                    'updated_at',
                ],
                'classes': ['collapse'],
            }
        ),
    ]
    def display_path_labels(self, obj):
        return ", ".join([label.name for label in obj.path_labels.all()])
    display_path_labels.short_description = 'Path Labels'

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # only on create
            obj.created_by = request.user

            # Assign first organization of this user
            org_user = OrganizationUser.objects.filter(user=request.user).first()
            if org_user:
                obj.organization = org_user.organization

        super().save_model(request, obj, form, change)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            # note: use <int:spoke_id>
            path('<int:spoke_id>/push/',
                 self.admin_site.admin_view(self.process_push),
                 name='spoke_push'),
        ]
        return custom + urls

    def push_button(self, obj):
        return format_html(
            '<a class="button" href="{}">Push</a>',
            f'./{obj.pk}/push/'
        )
    push_button.short_description = 'Action'
    push_button.allow_tags = True

    def last_push_message(self, obj):
        return obj.last_push_message or "—"

    last_push_message.short_description = "Message"


    def process_push(self, request, spoke_id):
        # enqueue
        
        spoke = Spoke.objects.get(pk=spoke_id)
        job = Job.objects.create(
            spoke=spoke,
            triggered_by=request.user,
            status="pending",
            message="Push scheduled"
    )
        spoke.last_push_message ="Push sheduled"
        spoke.save(update_fields=["last_push_message"])
        push_hub_spoke_tunnel_async.delay(spoke_id, job.id)
        self.message_user(
            request,
            "Push scheduled in background. Latest status will appear in list.",
            messages.INFO
        )
        return redirect(request.META.get('HTTP_REFERER', '../'))
    

   
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "device":
            # exclude any device used by a Hub or another Spoke
            hub_ids   = Hub.objects.values_list('local_device_id', flat=True)
            spoke_ids = Spoke.objects.values_list('device_id',      flat=True)
            tunnel_a_ids = Tunnel.objects.values_list('device_a_id', flat=True)
            tunnel_b_ids = Tunnel.objects.values_list('device_b_id', flat=True)
            used = set(hub_ids) | set(spoke_ids) | set(tunnel_a_ids) | set(tunnel_b_ids)
            kwargs["queryset"] = Device.objects.exclude(pk__in=used)
        if db_field.name == 'link_monitor':
            kwargs['queryset'] = LinkMonitoring.objects.filter(check_type='icmp')
        if db_field.name == 'domain_monitor':
            kwargs['queryset'] = LinkMonitoring.objects.filter(check_type='domain')
       
       
       
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
  
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # devices used by any Hub or Spoke
        used_hubs   = set(Hub.objects.values_list('local_device_id', flat=True))
        used_spokes = set(Spoke.objects.values_list('device_id',       flat=True))
        used        = used_hubs | used_spokes
        # when editing, allow the currently selected device
        if obj and obj.device_id:
            used.discard(obj.device_id)
        form.base_fields['device'].queryset = (
            Device.objects.exclude(pk__in=used)
        )
        return form
     

    def delete_model(self, request, obj):
        # obj.local_ip holds your management IP
        try:
            delete_tunnel_by_name(obj.hub_device.name, obj.local_ip)
        except TunnelAPIError as e:
            self.message_user(request,
                f"⚠️ Failed to delete tunnel on {obj.local_ip}: {e}",
                level=messages.ERROR
            )
            # if you want to abort the local delete, simply return here
            # return
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        errors = []
        for spoke in queryset:
            try:
                delete_tunnel_by_name(spoke.hub_device.name, spoke.local_ip)
            except TunnelAPIError as e:
                errors.append(f"{spoke.hub_device.name}@{spoke.local_ip}: {e}")
        if errors:
            self.message_user(request,
                "Some backend deletions failed:\n" + "\n".join(errors),
                level=messages.ERROR
            )
            # to abort the Django-side bulk delete, you could `return` here
        super().delete_queryset(request, queryset)




@admin.register(Hub)
class HubAdmin(admin.ModelAdmin):
    list_display = (
        'name','local_device',  'organization',
        'is_enabled','display_path_labels', 'created_by','last_pushed_at'
    )
    list_filter = (  'organization', 'is_enabled','path_labels')
    search_fields = ('name', 'organization')
 
    fieldsets = (
       
        (None, 
         {
            'fields': (
               'local_device', 'organization', 'name',  'created_by',
                'is_enabled', 
                 'wan_ip', 'subnet','forceencaps','dpdaction',  'ipcomp',
                
                
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
        (None, {'fields': ['path_labels']}),
        ('Status & Timestamps',
            {
                'fields': [
                    'uuid', 'local_ip', 
                    'last_pushed_at','last_config_hash','pre_shared_key','created_at',  'updated_at',
                'last_config_payload',
                ],
                'classes': ['collapse'],
            }
        ),
       
    )
    readonly_fields = ('last_config_hash','organization', 'last_pushed_at','pre_shared_key', 'created_by',
                       'last_config_payload','created_at', 'updated_at','uuid','local_ip'
                       )
   
   
   
   
    formfield_overrides = {
        models.CharField:       {'widget': forms.TextInput(attrs={'style': 'width:300px;'})},
        models.TextField:       {'widget': forms.Textarea(attrs={'style': 'width:300px;'})},
        models.ForeignKey:      {'widget': forms.Select(attrs={'style': 'width:300px;'})},
        models.PositiveIntegerField: {'widget': forms.NumberInput(attrs={'style': 'width:300px;'})},
        # Explicitly map BooleanField → CheckboxInput **without** styling
        models.BooleanField:    {'widget': forms.CheckboxInput(attrs={'style': 'width:100px;'})},
    }
    def display_path_labels(self, obj):
        return ", ".join([label.name for label in obj.path_labels.all()])
    display_path_labels.short_description = 'Path Labels'

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # only on create
            obj.created_by = request.user

            # Assign first organization of this user
            org_user = OrganizationUser.objects.filter(user=request.user).first()
            if org_user:
                obj.organization = org_user.organization

        super().save_model(request, obj, form, change)
   
   



    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "local_device":
            # exclude any device used by a Spoke or another Hub
            spoke_ids = Spoke.objects.values_list('device_id',       flat=True)
            hub_ids   = Hub.objects.values_list('local_device_id', flat=True)
            used = set(spoke_ids) | set(hub_ids)
            kwargs["queryset"] = Device.objects.exclude(pk__in=used)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    

    # def delete_model(self, request, obj):
    #     # obj.local_ip holds your management IP
    #     try:
    #         delete_tunnel_by_name(obj.name, obj.local_ip)
    #     except TunnelAPIError as e:
    #         self.message_user(request,
    #             f"⚠️ Failed to delete tunnel on {obj.local_ip}: {e}",
    #             level=messages.ERROR
    #         )
    #         # if you want to abort the local delete, simply return here
    #         # return
    #     super().delete_model(request, obj)

    # def delete_queryset(self, request, queryset):
    #     errors = []
    #     for hub in queryset:
    #         try:
    #             delete_tunnel_by_name(hub.name, hub.local_ip)
    #         except TunnelAPIError as e:
    #             errors.append(f"{hub.name}@{hub.local_ip}: {e}")
    #     if errors:
    #         self.message_user(request,
    #             "Some backend deletions failed:\n" + "\n".join(errors),
    #             level=messages.ERROR
    #         )
    #         # to abort the Django-side bulk delete, you could `return` here
    #     super().delete_queryset(request, queryset)

    def _delete_associated_spokes(self, request, hub):
        """
        Deletes all Spokes (API & DB) whose hub_device matches hub.local_device.
        """
        # related_spokes = Spoke.objects.filter(hub_device=hub.local_device)
        related_spokes = Spoke.objects.filter(hub_device=hub)
        errors = []

        for spoke in related_spokes:
            try:
                delete_tunnel_by_name(spoke.hub_device.name, spoke.local_ip)
            except TunnelAPIError as e:
                errors.append(
                    f"Spoke {spoke.device} (local_ip={spoke.local_ip}): {e}"
                )

        if errors:
            self.message_user(
                request,
                "Some Spoke deletions failed in backend API:\n" + "\n".join(errors),
                level=messages.ERROR
            )

    def delete_model(self, request, obj):
        # Step 1: Delete related Spokes in backend API
        self._delete_associated_spokes(request, obj)

        # Step 2: Delete this Hub in backend API
        try:
            delete_tunnel_by_name(obj.name, obj.local_ip)
        except TunnelAPIError as e:
            self.message_user(
                request,
                f"⚠️ Failed to delete Hub {obj.name} on {obj.local_ip}: {e}",
                level=messages.ERROR
            )

        # Step 3: Delete from DB (Spokes already cascaded in DB)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for hub in queryset:
            self._delete_associated_spokes(request, hub)
            try:
                delete_tunnel_by_name(hub.name, hub.local_ip)
            except TunnelAPIError as e:
                self.message_user(
                    request,
                    f"⚠️ Failed to delete Hub {hub.name}@{hub.local_ip}: {e}",
                    level=messages.ERROR
                )
        super().delete_queryset(request, queryset)

    def get_form(self, request, obj=None, **kwargs):

        form = super().get_form(request, obj, **kwargs)
        # get all Devices used by any Spoke or Hub
        used_spokes = set(Spoke.objects.values_list('device_id', flat=True))
        used_hubs   = set(Hub.objects.values_list('local_device_id', flat=True))
        used        = used_spokes | used_hubs
        # when editing, allow the currently selected device
        if obj and obj.local_device_id:
            used.discard(obj.local_device_id)
        # override the queryset for the foreignkey field
        form.base_fields['local_device'].queryset = (
            Device.objects.exclude(pk__in=used)
        )
        return form
    

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        'get_object',
        'triggered_by',
        'status',
        'short_message',
        'created_at',
        'finished_at',
    )
    list_filter = (
        'status',
        'created_at',
        'triggered_by',
    )
    search_fields = (
        'spoke_device_name',
        'tunnel_name',
        'message',
    )
    readonly_fields = (
        'spoke',
        'tunnel',
        'triggered_by',
        'status',
        'message',
        'created_at',
        'finished_at',
    )
    ordering = ('-created_at',)

    def get_object(self, obj):
        if obj.spoke:
            return f"Spoke: {obj.spoke.device.name}"
        if obj.tunnel:
            return f"Tunnel: {obj.tunnel.name}"
        return "—"
    get_object.short_description = "Target"

    def short_message(self, obj):
        return (obj.message[:50] + '...') if obj.message and len(obj.message) > 50 else obj.message
    short_message.short_description = "Message"


@admin.register(PathLabel)
class PathLabelAdmin(admin.ModelAdmin):
    form = PathLabelForm
    list_display = ('name', 'description', 'direct_internet_access','color_preview', 'created_at')

    def color_preview(self, obj):
        return format_html(
            '<div style="width: 30px; height: 20px; background-color: {}; border: 1px solid #000;"></div>',
            obj.color
        )
    color_preview.short_description = "Color"

@admin.register(LinkMonitoring)
class LinkMonitoringAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'service', 'check_type', 'source_interface',
        'destination', 'time_interval', 'retry_times',
        'time_out_action', 'created_at'
    )
    list_filter = ('service', 'check_type', 'time_out_action', 'created_at')
    search_fields = ('name', 'destination', 'source_interface')
    fieldsets = (
       
        (None, 
         {
            'fields': (
               'name', 'service', 'check_type',  'source_interface',
                'destination', 
                 
                'time_out_action', 
                'time_interval','retry_times',  'custom_command',
                
                
            )
        }),)
    ordering = ('-created_at',)



@admin.register(QOSPolicy)
class QOSPolicyAdmin(admin.ModelAdmin):
    form = QOSPolicyForm
    list_display = (
        'name', 'realtime_bandwidth_limit', 'control_signaling_weight',
        'prime_select_weight', 'standard_select_weight', 'best_effort_weight',
        'inbound_enabled', 'enforce_rx_limit', 'created_at'
    )
    list_filter = ('inbound_enabled', 'enforce_rx_limit')
    search_fields = ('name',)
    readonly_fields = ('created_at',)
    fieldsets = [
        (None, {'fields': ['name', 'description']}),
        ('Outbound QoS Plan', {'fields': [
            'realtime_bandwidth_limit', 'realtime_dscp',
            'control_signaling_weight', 'control_signaling_dscp',
            'prime_select_weight', 'prime_select_dscp',
            'standard_select_weight', 'standard_select_dscp',
            'best_effort_weight', 'best_effort_dscp'
        ]}),
        ('Inbound QoS Plan', {'fields': [
            'inbound_enabled', 'enforce_rx_limit',
            'high_bandwidth_limit', 'medium_bandwidth_limit', 'low_bandwidth_limit'
        ]}),
        ('Timestamps', {'fields': ['created_at'], 'classes': ['collapse']}),
    ]
    class Media:
        css = {
            'all': ('admin/css/slider_styles.css',)
        }
        js = ('admin/js/slidervalue.js',)


@admin.register(Firewall)
class FirewallAdmin(admin.ModelAdmin):
    list_display = ('name',  'created_at')




@admin.register(SDWANZone)
class SDWANZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'interface_name', 'created_at')




@admin.register(FullMesh)
class FullMeshAdmin(admin.ModelAdmin):
    form = FullMeshForm

    list_display = ('name', 'is_enabled', 'edges_count', 'updated_at')
    search_fields = ('name',)
    list_filter = ('is_enabled',)
    list_display_links = ('name',)

    fieldsets = (
        ('Details', {'fields': ('name', 'description', 'is_enabled')}),
        ('Devices (table)', {'fields': ('members',)}),
        ('Policy (applies to entire mesh)', {
            'fields': (
                ('ike_version','ike_encryption_algorithm','ike_integrity_algorithm'),
                ('ike_diffie_hellman_group','ike_key_lifetime'),
                ('esp_version','esp_encryption_algorithm','esp_integrity_algorithm'),
                ('esp_diffie_hellman_group','esp_key_lifetime'),
                ('dpdaction','ipcomp'),
                'pre_shared_key',
            )
        }),
        ('Preview', {'fields': ('pairs_preview',)}),
        ('Meta (auto)', {
            'classes': ('collapse',),
            'fields': ('organization','created_by','created_at','updated_at'),
        }),
    )
    readonly_fields = ('pairs_preview', 'organization','created_by','created_at','updated_at')

    def pairs_preview(self, obj: FullMesh):
        if not obj or obj.pk is None:
            return "Save to see the computed pairs."
        rows = obj.pair_table()
        if not rows:
            return "No pairs to show (need at least 2 enabled devices)."

        # simple HTML table (like your CSV)
        html = [
            '<div style="max-height:420px; overflow:auto;">',
            '<table class="adminlist table" style="min-width:760px">',
            '<thead><tr>',
            '<th>#</th><th>Device A</th><th>WAN A</th><th>Subnet A</th>',
            '<th>Device B</th><th>WAN B</th><th>Subnet B</th>',
            '<th>Status</th><th>Last Pushed</th>',
            '</tr></thead><tbody>',
        ]
        for r in rows:
            html.append(
                f"<tr><td>{r['#']}</td>"
                f"<td>{r['Device A']}</td><td>{r['WAN A']}</td><td>{r['Subnet A']}</td>"
                f"<td>{r['Device B']}</td><td>{r['WAN B']}</td><td>{r['Subnet B']}</td>"
                f"<td>{r.get('Status','')}</td><td>{r.get('Last Pushed','') or '—'}</td></tr>"
            )
        html.append('</tbody></table></div>')
        return mark_safe(''.join(html))

    pairs_preview.short_description = "Pairwise tunnels preview"

    @admin.display(description='Preview')
    def preview_link(self, obj):
        url = reverse('admin:sdwan_tunnel_fullmesh_preview', args=[obj.pk])
        return mark_safe(f'<a class="button" href="{url}">View pairs</a>')

    def get_urls(self):
        urls = super().get_urls()
        my = [
            path(
                '<path:object_id>/preview/',
                self.admin_site.admin_view(self.preview_view),
                name='sdwan_tunnel_fullmesh_preview',
            ),
        ]
        return my + urls

    def preview_view(self, request, object_id):
        obj = get_object_or_404(FullMesh, pk=object_id)
        rows = obj.pair_table()  # produces: #, Device A, WAN A, Subnet A, Device B, WAN B, Subnet B, Status, Last Pushed
        ctx = dict(self.admin_site.each_context(request), title=f'{obj.name} — Pairs', object=obj, rows=rows)
        # Render a very simple table without adding a template file:
        table = ['<table class="table table-sm table-striped"><thead><tr>',
                 '<th>#</th><th>Device A</th><th>WAN A</th><th>Subnet A</th>',
                 '<th>Device B</th><th>WAN B</th><th>Subnet B</th><th>Status</th><th>Last Pushed</th>',
                 '</tr></thead><tbody>']
        for r in rows:
            table.append(
                f"<tr><td>{r['#']}</td><td>{r['Device A']}</td><td>{r['WAN A']}</td><td>{r['Subnet A']}</td>"
                f"<td>{r['Device B']}</td><td>{r['WAN B']}</td><td>{r['Subnet B']}</td>"
                f"<td>{r.get('Status','')}</td><td>{r.get('Last Pushed','') or '—'}</td></tr>"
            )
        table.append('</tbody></table>')
        ctx['content'] = mark_safe(''.join(table))
        return TemplateResponse(request, 'admin/base_site.html', ctx)