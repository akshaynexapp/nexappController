# sdwan_tunnel/management/commands/run_spoke_status.py
import time, logging
from django.core.management.base import BaseCommand
from sdwan_tunnel.tasks import update_all_tunnel_statuses
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Continuously update all tunnel and spoke statuses every 30 seconds"

    def add_arguments(self, parser):
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run a single update cycle and then exit'
        )

    def handle(self, *args, **options):
        once = options.get('once', False)
        logger.info(
            "Starting tunnel+spoke status loop (every 30s) %s",
            "(single run)" if once else ""
        )
        while True:
            try:
                # Execute the task synchronously
                update_all_tunnel_statuses.run()
                logger.info("Completed one update_all_tunnel_statuses cycle")
            except Exception:
                logger.exception("Error in update_all_tunnel_statuses")

            if once:
                logger.info("Completed one update cycle; exiting")
                break

            # Sleep 30 seconds before next run
            time.sleep(30)
