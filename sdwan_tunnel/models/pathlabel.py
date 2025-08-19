# models.py
from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()
from django.core.exceptions import ValidationError


class PathLabel(models.Model):
    CHOICES = [
        ('yes', 'Yes'),
        ('no',  'No'),
    ]
    name = models.CharField(max_length=128, unique=True)
    description = models.CharField(max_length=128, unique=True)
    color = models.CharField(max_length=7, help_text="Pick a color", default="#000000")
    direct_internet_access = models.CharField(max_length=5, choices=CHOICES, default='No')  # ✅ Toggle Field
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']