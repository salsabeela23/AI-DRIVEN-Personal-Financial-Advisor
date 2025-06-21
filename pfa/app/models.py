import datetime
import os

# Create your models here.

# models.py
from django.db import models

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pfa.settings')


class UserDetails(models.Model):
    objects = models.Manager()
    uid = models.CharField(max_length=128, unique=True)
    email = models.EmailField(unique=True, default="N/A")
    id_token = models.CharField(unique=True, max_length=1000)
    display_name = models.CharField(max_length=256, default="N/A")
    created_at = models.DateTimeField(default=datetime.datetime.now)


class UserPreference(models.Model):
    objects = models.Manager()
    uid = models.CharField(max_length=255, unique=True)  # Store the UID as a string


class UserProfile(models.Model):
    objects = models.Manager()
    name = models.CharField(max_length=100)
    email = models.EmailField()
    total_savings = models.DecimalField(max_digits=10, decimal_places=2)
    risk_tolerance = models.CharField(max_length=10, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')])
    time_horizon = models.IntegerField()  # in years


class Recommendation(models.Model):
    objects = models.Manager()
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    investment_type = models.CharField(max_length=100)
    allocation_percentage = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
