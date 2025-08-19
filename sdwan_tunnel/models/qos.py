from django.db import models
from django.core.exceptions import ValidationError
from django.contrib import admin
from django import forms
from rest_framework import serializers

class QOSPolicy(models.Model):
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    # Choice sets for percentages and DSCP
    PERCENT_CHOICES = [(i, f"{i}%") for i in range(10, 71, 10)]
    DSCP_CHOICES = [
        ('CS0', 'CS0'), ('CS1', 'CS1'), ('CS2', 'CS2'), ('CS3', 'CS3'),
        ('CS4', 'CS4'), ('CS5', 'CS5'), ('CS6', 'CS6'), ('CS7', 'CS7'),
    ]

    # Outbound QoS Plan
    realtime_bandwidth_limit = models.PositiveIntegerField(
        choices=PERCENT_CHOICES,
        default=30,
        help_text='As percentage of WAN bandwidth (10–70%)'
    )
    realtime_dscp = models.CharField(
        max_length=3,
        choices=DSCP_CHOICES,
        default='CS0'
    )

    control_signaling_weight = models.PositiveIntegerField(
        choices=PERCENT_CHOICES,
        default=40,
        help_text='Control-Signaling queue weight (10–70%)'
    )
    control_signaling_dscp = models.CharField(
        max_length=3,
        choices=DSCP_CHOICES,
        default='CS0'
    )

    prime_select_weight = models.PositiveIntegerField(
        choices=PERCENT_CHOICES,
        default=30,
        help_text='Prime-Select queue weight (10–70%)'
    )
    prime_select_dscp = models.CharField(
        max_length=3,
        choices=DSCP_CHOICES,
        default='CS0'
    )

    standard_select_weight = models.PositiveIntegerField(
        choices=PERCENT_CHOICES,
        default=20,
        help_text='Standard-Select queue weight (10–70%)'
    )
    standard_select_dscp = models.CharField(
        max_length=3,
        choices=DSCP_CHOICES,
        default='CS0'
    )

    best_effort_weight = models.PositiveIntegerField(
        choices=PERCENT_CHOICES,
        default=10,
        help_text='Best-Effort queue weight (10–70%)'
    )
    best_effort_dscp = models.CharField(
        max_length=3,
        choices=DSCP_CHOICES,
        default='CS0'
    )

    # Inbound QoS Plan
    inbound_enabled = models.BooleanField(
        default=False,
        help_text='Enable inbound QoS plan'
    )
    enforce_rx_limit = models.BooleanField(
        default=False,
        help_text='Enforce RX bandwidth limits'
    )
    high_bandwidth_limit = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='High importance RX limit as percentage'
    )
    medium_bandwidth_limit = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Medium importance RX limit as percentage'
    )
    low_bandwidth_limit = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Low importance RX limit as percentage'
    )

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        super().clean()
        # Validate outbound weights sum
        total = (
            self.control_signaling_weight +
            self.prime_select_weight +
            self.standard_select_weight +
            self.best_effort_weight
        )
        if total != 100:
            raise ValidationError('Sum of outbound data queue weights must equal 100%')
        # Validate inbound limits ordering
        if self.inbound_enabled and self.enforce_rx_limit:
            limits = [
                self.high_bandwidth_limit,
                self.medium_bandwidth_limit,
                self.low_bandwidth_limit
            ]
            if any(v is None for v in limits):
                raise ValidationError('All inbound bandwidth limits must be set when enforcement is enabled')
            if not (limits[0] >= limits[1] >= limits[2]):
                raise ValidationError('Inbound limits must be in descending order: High ≥ Medium ≥ Low')

    def __str__(self):
        data_total = (
            self.control_signaling_weight +
            self.prime_select_weight +
            self.standard_select_weight +
            self.best_effort_weight
        )
        return f"{self.name} (Realtime {self.realtime_bandwidth_limit}%, Data {data_total}%)"
