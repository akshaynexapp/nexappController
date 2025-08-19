from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()
from django.core.exceptions import ValidationError



class Category(models.Model):
    application_index = models.PositiveIntegerField(unique=True, help_text="Netify category/tag id")
    name = models.SlugField(max_length=64, unique=True)
    label = models.CharField(max_length=128)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["label"]

    def __str__(self):
        return self.label