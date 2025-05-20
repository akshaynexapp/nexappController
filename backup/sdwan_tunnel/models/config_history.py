
# sdwan_tunnel/models/config_history.py
"""
Stores snapshots for rollback and audit.
Fields:
- FK to Tunnel, user, action
- JSON payload and its SHA-256 hash
- Timestamp and raw config text
"""
from django.db import models
from django.contrib.auth import get_user_model
from .tunnel import Tunnel
from openwisp_users.models import OrganizationUser


User = get_user_model()

class ConfigHistory(models.Model):
    # user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    # tunnel = models.ForeignKey(Tunnel, on_delete=models.CASCADE, related_name='config_histories')
    # payload_hash = models.CharField(max_length=64)
    # payload = models.JSONField()
    # config_text = models.TextField(null=True, blank=True)
    # action = models.CharField(max_length=20, help_text='push, delete or rollback')
    # timestamp = models.DateTimeField(auto_now_add=True)
    # generated_at = models.DateTimeField(auto_now_add=True)
    # triggered_by = models.ForeignKey(OrganizationUser, on_delete=models.SET_NULL, null=True)

    ACTION_CHOICES = [
        ('push', 'push'),
        ('delete', 'delete'),
        ('rollback', 'rollback'),
    ]

    tunnel = models.ForeignKey(Tunnel, on_delete=models.CASCADE)
    payload = models.JSONField(help_text='The list of API payload calls')
    config_hash = models.CharField(max_length=64)
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        help_text="push, delete or rollback"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Order by creation time descending instead of non-existent 'timestamp'
        ordering = ['-created_at']

  
    
    def __str__(self):
        return f"{self.tunnel.name} [{self.action}] @ {self.created_at:%Y-%m-%d %H:%M:%S}"  

    # def __str__(self):
    #     return f"{self.action} for {self.tunnel.name} @ {self.timestamp}"
