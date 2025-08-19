# models.py
from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()
from django.core.exceptions import ValidationError

# application/models.py

class Category(models.Model):
    tag_id = models.PositiveIntegerField(unique=True, help_text="Netify category/tag id")
    name = models.SlugField(max_length=64, unique=True)
    label = models.CharField(max_length=128)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["label"]

    def __str__(self):
        return self.label


class Application(models.Model):
    # app_id = models.PositiveIntegerField(unique=True, help_text="Netify application id")
    # e.g. "netify.netflix"
   
    category = models.ForeignKey(
        Category,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="applications",
    )
    # list of hostnames/SNI/domains from the signatures file
    domains = models.JSONField(default=list, blank=True)
    # anything else you want to keep (protocols, tags, etc.)

    # app_id = models.PositiveIntegerField(unique=True , default='0')
    application_name = models.CharField(max_length=255, db_index=True)

    # NEW:

    meta = models.JSONField(default=dict, blank=True)
    last_update = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["application_name"]

    def __str__(self):
        return self.application_name
