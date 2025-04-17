from django.db import models

# Create your models here.
class Department(models.Model):
    name = models.CharField(max_length=100, null=False)
    location = models.CharField(max_length=100)

class Role(models.Model):
    name = models.CharField(max_length=100, null=False)
    
class Employee(models.Model):
    first_name = models.CharField(max_length=100, null=False)
    last_name = models.CharField(max_length=100)
    dept = models.ForeignKey(Department, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)