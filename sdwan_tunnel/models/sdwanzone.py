# models.py
from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()
from django.core.exceptions import ValidationError


class SDWANZone(models.Model):
 
    name = models.CharField(max_length=128, unique=True)
    interface_name = models.CharField(max_length=128,null=False,blank=False )
    
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']