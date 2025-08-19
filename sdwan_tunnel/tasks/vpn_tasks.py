from celery import shared_task
import logging
from django.core.cache import cache

from django.utils import timezone
logger = logging.getLogger(__name__)
@shared_task
def push_tunnel_async(tunnel_id ,job_id):
    from sdwan_tunnel.models import Tunnel  # note naming

    from sdwan_tunnel.models import  Job
    try:
        tunnel = Tunnel.objects.get(pk=tunnel_id)
        result = tunnel.push_to_agent(job_id=job_id, full_replace=False)
        # TunnelStatus.objects.create(
        #     tunnel=tunnel,
        #     is_up=(result.get("status") == "success") or (result.get("status") == "error"),
        #     timestamp=timezone.now()
        # )
        return result




    except Exception as exc:
        logger.exception(f"push_tunnel_async failed for Tunnel {tunnel_id}")
        job = Job.objects.filter(pk=job_id).first()
        if job:
            job.status = "failure"
            job.message = str(exc)
            job.finished_at = timezone.now()
            job.save(update_fields=['status', 'message', 'finished_at'])
        return {"status": "error", "message": str(exc)}

 
