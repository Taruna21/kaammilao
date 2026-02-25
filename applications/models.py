from django.db import models
from users.models import User
from jobs.models import Job


class Application(models.Model):

    STATUS_CHOICES = [
        ('pending',     'Pending'),
        ('shortlisted', 'Shortlisted'),
        ('rejected',    'Rejected'),
        ('hired',       'Hired'),
    ]

    job       = models.ForeignKey(Job,  on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_applications')

    status    = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    note      = models.TextField(blank=True)   # seeker can add a short note while applying
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-applied_at']
        # prevent same person applying to same job twice
        unique_together = ['job', 'applicant']

    def __str__(self):
        return f"{self.applicant.phone} → {self.job.title} ({self.status})"