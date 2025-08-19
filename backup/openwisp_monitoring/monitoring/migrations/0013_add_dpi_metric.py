from django.db import migrations

def add_dpi_metric(apps, schema_editor):
    Metric = apps.get_model('monitoring', 'Metric')
    if not Metric.objects.filter(name='dpi').exists():
        Metric.objects.create(
        name='dpi',
        field_name='bytes', # primary field to aggregate
        main_tags={'host': ''}, # main dimension tag
        extra_tags={ # additional tag dimensions
        'app': '',
        'src': '',
        'dst': ''
        },
        
        )

def remove_dpi_metric(apps, schema_editor):
    Metric = apps.get_model('monitoring', 'Metric')
    Metric.objects.filter(name='dpi').delete()

class Migration(migrations.Migration):
    dependencies = [
    ('monitoring', '0012_migrate_signal_metrics'),
    ]
    operations = [
    migrations.RunPython(add_dpi_metric, remove_dpi_metric),
    ]