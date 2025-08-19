import requests
import logging
from celery import shared_task
from redis.exceptions import ResponseError
from kombu.exceptions import OperationalError
from openwisp_monitoring.device.models import SpokeStatus, IpsecTunnels

from django.utils import timezone
from datetime import datetime, timedelta



logger = logging.getLogger(__name__)


@shared_task(bind=True, ignore_result=True, max_retries=None)
def update_all_tunnel_statuses(self):
    try:
        update_spoke_status()
        update_tunnel_status()


        self.apply_async(
        eta=datetime.utcnow() + timedelta(seconds=30),
        expires=35  # optional safety to prevent backlog
    )
        # self.apply_async(countdown=30)
    except (ResponseError, OperationalError) as exc:
        logger.warning(f"Could not reschedule tunnel update: {exc!r}")



def update_spoke_status():
    from sdwan_tunnel.models import Spoke
    try:
        for spoke in Spoke.objects.all():
        # 1) grab the latest ipsec report for this spoke
            report = (IpsecTunnels.objects
                .filter(device_id=spoke.uuid)
                .order_by('-timestamp')
                .first()
             )
            if not report:
                logger.warning("No IpsecTunnels for %s", spoke.uuid)
                continue

            tunnels = report.raw.get('tunnels', [])
    
            if not tunnels:
                logger.warning("Empty tunnels list for %s", spoke.uuid)
                spoke.status = 'pending'
                continue


       
            match = next(
                (t for t in tunnels if spoke.subnet in t.get('remote', []) or spoke.subnet in t.get('local', [])),
                None
            )
    
            if match:
                spoke.status = 'active' if match.get('connected') else 'error'
            else:
                logger.warning(
                    "No tunnel for subnet %r on spoke %s", spoke.subnet, spoke.uuid
                )
                spoke.status = 'error'
       
       
        # 3) grab the latest health record
            health = (
                SpokeStatus.objects
                .filter(device_id=spoke.uuid)
                .order_by('-timestamp')
                .first()
)    
            if health and 'tunnel_health' in health.raw:
                th = health.raw['tunnel_health']
                # only use these metrics if the probe came from this spoke's hub device
                expected_source = spoke.device.name
                if th.get('source') == expected_source:
                    spoke.latency     = th.get('latency')
                    spoke.jitter      = th.get('jitter')
                    spoke.packet_loss = th.get('loss')
                else:
                    # probe came from the wrong source → show as N/A
                    spoke.latency = None
                    spoke.jitter = None
                    spoke.packet_loss = None
            else:
                spoke.latency = spoke.jitter = spoke.packet_loss = None
            
                    # 4) save
            spoke.save(update_fields=[
                'status', 'latency', 'jitter', 'packet_loss'
            ])
    
    
        # reschedule
            

    except (ResponseError, OperationalError) as exc:
        # Log the Redis write-error, but don’t bubble it up
        logger.warning(f"Could not reschedule task: {exc!r}")


# def update_tunnel_status():
#     from sdwan_tunnel.models import Tunnel

#     for tunnel in Tunnel.objects.all():
#         # Try both sides (device_a = uuid_a, device_b = uuid_b)
#         updated = False
#         for uuid, subnet in [(tunnel.uuid_a, tunnel.device_a_subnet), (tunnel.uuid_b, tunnel.device_b_subnet)]:
#             report = (
#                 IpsecTunnels.objects
#                 .filter(device_id=uuid)
#                 .order_by('-timestamp')
#                 .first()
#             )
#             if not report:
#                 continue

#             tunnels = report.raw.get('tunnels', [])
#             match = next(
#                 (t for t in tunnels if subnet in t.get('remote', []) or subnet in t.get('local', [])),
#                 None
#             )
#             if match:
#                 tunnel.status = 'active' if match.get('connected') else 'error'
#                 updated = True
#                 break  # once one side is found, we’re done

#         # if not updated:
#         #     tunnel.status = 'pending'
#             health = (
#                 SpokeStatus.objects
#                 .filter(device_id=uuid)
#                 .order_by('-timestamp')
#                 .first()
# )    
#             if health and 'tunnel_health' in health.raw:
#                 th = health.raw['tunnel_health']
#                 # only use these metrics if the probe came from this spoke's hub device
#                 expected_source = tunnel.device_a.name or tunnel.device_b.name
#                 # if th.get('source') == expected_source:
#                 tunnel.latency     = th.get('latency')
#                 tunnel.jitter      = th.get('jitter')
#                 tunnel.packet_loss = th.get('loss')
#                 # else:
#                 #     # probe came from the wrong source → show as N/A
#                 #     tunnel.latency = None
#                 #     tunnel.jitter = None
#                 #     tunnel.packet_loss = None
#             else:
#                 tunnel.latency = tunnel.jitter = tunnel.packet_loss = None
            
#                     # 4) save
#             # tunnel.save(update_fields=[
#             #     'status', 'latency', 'jitter', 'packet_loss'
#             # ])

#         tunnel.save(update_fields=['status', 'latency', 'jitter', 'packet_loss'])


def update_tunnel_status():
    from sdwan_tunnel.models import Tunnel
    from django.db.models import F

    for tunnel in Tunnel.objects.all():
        # 1) figure out which device/UUID to query the health for
        #    (we try both ends and stop on the first that has data)
        metric_found = False
        for uuid in (tunnel.uuid_a, tunnel.uuid_b):
            # fetch the latest ipsec snapshot if you need status too
            report = (
                IpsecTunnels.objects
                .filter(device_id=uuid)
                .order_by('-timestamp')
                .first()
            )
            if report:
                # update tunnel.status from that report (same logic as spokes)
                match = next(
                    (t for t in report.raw.get('tunnels', [])
                     if tunnel.device_a_subnet in t.get('local', []) 
                     or tunnel.device_a_subnet in t.get('remote', [])),
                    None
                )
                if match:
                    tunnel.status = 'active' if match.get('connected') else 'error'
                    metric_found = True
                    break

        # 2) fetch the latest health metrics for the same uuid
        health = (
            SpokeStatus.objects
            .filter(device_id=uuid)
            .order_by('-timestamp')
            .first()
        )
        if health and 'tunnel_health' in health.raw:
            th = health.raw['tunnel_health']
            tunnel.latency     = th.get('latency')
            tunnel.jitter      = th.get('jitter')
            tunnel.packet_loss = th.get('loss')
        else:
            tunnel.latency = tunnel.jitter = tunnel.packet_loss = None

        # 3) write them back
        tunnel.save(update_fields=['status', 'latency', 'jitter', 'packet_loss'])