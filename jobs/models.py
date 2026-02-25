from django.db import models
from users.models import User

class Job(models.Model):
    CATEGORY_CHOICES = [
        ('plumber',     'Plumber'),
        ('cook',        'Cook'),
        ('maid',        'Maid'),
        ('painter',     'Painter'),
        ('sweeper',     'Sweeper'),
        ('dishwasher',  'Dishwasher'),
        ('electrician', 'Electrician'),
        ('mechanic',    'Mechanic'),
        ('driver',      'Driver'),
        ('gardener',    'Gardener'),
    ]

    STATUS_CHOICES = [
        ('open',   'Open'),
        ('closed', 'Closed'),
        ('hired',  'Hired'),
    ]

    PAY_TYPE_CHOICE = [
        ('daily',   'Per Day'),
        ('monthly', 'Per Month'),
        ('hourly',  'Per Hour'),
    ]

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=200, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)

    city = models.CharField(max_length=100)
    area = models.CharField(max_length=100)
    pincode = models.CharField(max_length=6, blank=True)

    pay_amount = models.DecimalField(max_digits=8, decimal_places=2)
    pay_type = models.CharField(max_length=20, choices=PAY_TYPE_CHOICE, default='daily')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']   # newest jobs first by default

    def __str__(self):
        return f"{self.title} - {self.city} ({self.status})"


