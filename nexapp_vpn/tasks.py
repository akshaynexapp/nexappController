from celery import shared_task
from django.utils import timezone
from .models import Tunnel, TunnelStatusLog
 
@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def push_tunnel_async(self, tunnel_id):
    try:
        tunnel = Tunnel.objects.get(pk=tunnel_id)
        result = tunnel.push_to_agent()
        # record a status log for UI visibility
        TunnelStatusLog.objects.create(
            tunnel=tunnel,
            status=result.get('status'),
            log=result.get('message') or str(result),
            timestamp=timezone.now()
        )
        return result
    except Exception as exc:
        # retry up to 3 times with 10s delay
        raise self.retry(exc=exc)