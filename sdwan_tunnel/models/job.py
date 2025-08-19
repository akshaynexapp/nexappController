# models.py
from django.db import models
from django.contrib.auth import get_user_model
from sdwan_tunnel.models import Spoke , Tunnel
User = get_user_model()
from django.core.exceptions import ValidationError


class Job(models.Model):
    STATUS_CHOICES = [
        ('pending', '⏳ Pending'),
        ('success', '✅ Success'),
        ('failure', '❌ Failure'),
    ]

    spoke = models.ForeignKey(Spoke, null=True, blank=True, on_delete=models.CASCADE, related_name='push_jobs')
    tunnel = models.ForeignKey(Tunnel, null=True, blank=True, on_delete=models.CASCADE, related_name='push_jobs')
    triggered_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        if self.spoke:
            return f"{self.spoke.device.name} - {self.get_status_display()}"
        elif self.tunnel:
            return f"{self.tunnel.name} - {self.get_status_display()}"
        return f"Unknown Job - {self.get_status_display()}"

    class Meta:
        ordering = ['-created_at']
    
    def clean(self):
        super().clean()
        if not self.spoke and not self.tunnel:
            raise ValidationError("Job must be linked to either a spoke or a tunnel.")
        if self.spoke and self.tunnel:
            raise ValidationError("Job cannot be linked to both a spoke and a tunnel.")
