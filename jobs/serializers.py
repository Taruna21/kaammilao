from rest_framework import serializers
from .models import Job
from users.models import User


class RecruiterBasicSerializer(serializers.ModelSerializer):
    """Shows basic recruiter info inside a job listing."""
    class Meta:
        model  = User
        fields = ['id', 'full_name', 'phone', 'city']


class JobSerializer(serializers.ModelSerializer):
    # Nest recruiter info inside the job response (read only)
    posted_by = RecruiterBasicSerializer(read_only=True)

    # Extra computed fields
    pay_display = serializers.SerializerMethodField()

    class Meta:
        model  = Job
        fields = [
            'id', 'title', 'category', 'description',
            'city', 'area', 'pincode',
            'pay_amount', 'pay_type', 'pay_display',
            'status', 'posted_by', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'posted_by']

    def get_pay_display(self, obj):
        """Returns something like ₹500/day instead of raw numbers."""
        type_map = {'daily': 'day', 'monthly': 'month', 'hourly': 'hour'}
        return f"₹{obj.pay_amount}/{type_map.get(obj.pay_type, obj.pay_type)}"


class JobCreateSerializer(serializers.ModelSerializer):
    """Used when a recruiter creates/edits a job."""
    class Meta:
        model  = Job
        fields = [
            'title', 'category', 'description',
            'city', 'area', 'pincode',
            'pay_amount', 'pay_type'
        ]

    def create(self, validated_data):
        # Automatically attach the logged-in recruiter as posted_by
        request = self.context['request']
        job = Job.objects.create(posted_by=request.user, **validated_data)
        return job