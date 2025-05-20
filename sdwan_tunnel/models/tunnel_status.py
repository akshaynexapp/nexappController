
# sdwan_tunnel/models/tunnel_status.py
"""
Records live health metrics per tunnel.
Fields:
- FK to Tunnel, up/down, latency, jitter, packet_loss, timestamp
"""
from django.db import models



class TunnelStatus(models.Model):
    tunnel = models.ForeignKey('Tunnel', on_delete=models.CASCADE, related_name='statuses')
    is_up = models.BooleanField()
    latency_ms = models.FloatField(null=True)
    jitter_ms = models.FloatField(null=True)
    packet_loss_percent = models.FloatField(null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [models.Index(fields=['tunnel', 'timestamp'])]
        verbose_name = 'Tunnel Status'
        verbose_name_plural = 'Tunnel Statuses'

    def __str__(self):
        return f"Status for {self.tunnel.name} @ {self.timestamp}"

