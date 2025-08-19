
from django.core.management.base import BaseCommand

 
class Command(BaseCommand):
    help = 'Purge DPI records older than 365 days'
 
    def handle(self, *args, **options):  # accept verbosity and other options
        """
        Deletes DPIRecord entries older than the retention period.
        """
 
        """
        Deletes all DPIRecord entries older than the retention period.
        """
        from datetime import timedelta
        from django.utils import timezone
        from openwisp_monitoring.device.models import DPIRecord
 
        # Calculate cutoff datetime
        cutoff = timezone.now() - timedelta(days=365)
        deleted,  _= DPIRecord.objects.filter(timestamp__lt=cutoff).delete()
        self.stdout.write(f"Deleted {deleted} old DPI records.")
        cutoff = timezone.now() - timedelta(days=365)
        deleted,  __= DPIRecord.objects.filter(timestamp__lt=cutoff).delete()
        self.stdout.write(f"Deleted {deleted} old DPI records")