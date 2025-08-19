from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import urllib3
import requests
User = get_user_model()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class LinkMonitoring(models.Model):
    name = models.CharField(max_length=128, unique=True)
    service = models.CharField(
        max_length=16,
        choices=[('enable', 'Enable'), ('disable', 'Disable')],
        default='disable'
    )
    check_type = models.CharField(
        max_length=32,
        choices=[('icmp', 'ICMP'), ('domain', 'Domain')],
        default='icmp'
    )
    source_interface = models.CharField(
        max_length=64,
        choices=[
            ('eth0', 'eth0'), ('eth1', 'eth1'), ('eth2', 'eth2'),
            ('eth3', 'eth3'), ('eth4', 'eth4'), ('eth5', 'eth5')
        ],
        default='eth0'
    )
    destination = models.GenericIPAddressField()
    time_interval = models.PositiveIntegerField(help_text='Time interval in seconds')
    retry_times = models.PositiveIntegerField()
    time_out_action = models.CharField(
        max_length=32,
        choices=[('reboot', 'Reboot'), ('custom', 'Custom')],
        default='custom'
    )
    custom_command = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Persist locally first
        super().save(*args, **kwargs)

        # Prepare payload for external ICMP check API
        payload = {
            "method": "set-config",
            "payload": [{
                "service": self.service,
                "name": self.name,
                "check_type": self.check_type,
                "source_interface": self.source_interface,
                "destination": str(self.destination),
                "time_interval": str(self.time_interval),
                "retry_times": str(self.retry_times),
                "time_out_action": self.time_out_action,
                "custom_command": self.custom_command or ""
            }]
        }

        try:
            response = requests.post(
                url = f"https://{self.destination}/api-new/icmpcheck",
                json=payload,
                timeout=10,
                verify=False
            )
            response.raise_for_status()
        except requests.RequestException as e:
            # Rollback external API failure
            raise ValidationError(f"External ICMP API call failed: {e}")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']
