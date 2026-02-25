from rest_framework import serializers
from .models import Application
from jobs.serializers import JobSerializer


class ApplicationSerializer(serializers.ModelSerializer):
    # Show full job details inside each application
    job_detail = JobSerializer(source='job', read_only=True)
    applicant_name = serializers.CharField(source='applicant.full_name', read_only=True)
    applicant_phone = serializers.CharField(source='applicant.phone', read_only=True)

    class Meta:
        model  = Application
        fields = [
            'id', 'job', 'job_detail',
            'applicant_name', 'applicant_phone',
            'status', 'note', 'applied_at'
        ]
        read_only_fields = ['id', 'status', 'applied_at']


class ApplicationStatusSerializer(serializers.ModelSerializer):
    """Only recruiters use this — to update application status."""
    class Meta:
        model  = Application
        fields = ['status']