
# sdwan_tunnel/models/audit_log.py
"""
AuditLogEntry for tracking user operations.
Fields:
- FK to User, event code, FK to Topology, list of device IDs, optional details, timestamp
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class AuditLogEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    event = models.CharField(max_length=50)
    topology_id = models.IntegerField()
    devices = models.JSONField(help_text='List of OpenWISP Device IDs')
    details = models.JSONField(null=True, blank=True, help_text='Additional event context')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log Entry'
        verbose_name_plural = 'Audit Log Entries'

    def __str__(self):
        return f"{self.event} by {self.user} @ {self.timestamp}"

