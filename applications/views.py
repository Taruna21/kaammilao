from rest_framework import generics, permissions
from rest_framework.response import Response
from .models import Application
from .serializers import ApplicationSerializer, ApplicationStatusSerializer


class ApplyToJobView(generics.CreateAPIView):
    """
    POST /api/applications/apply/
    Job seeker applies to a job.
    """
    serializer_class   = ApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(applicant=self.request.user)


class MyApplicationsView(generics.ListAPIView):
    """
    GET /api/applications/mine/
    Seeker sees all their applications + current status.
    """
    serializer_class   = ApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Application.objects.filter(applicant=self.request.user)


class JobApplicationsView(generics.ListAPIView):
    """
    GET /api/applications/job/<job_id>/
    Recruiter sees all applicants for their job.
    """
    serializer_class   = ApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        job_id = self.kwargs['job_id']
        return Application.objects.filter(
            job__id=job_id,
            job__posted_by=self.request.user  # only their own job
        )


class UpdateApplicationStatusView(generics.UpdateAPIView):
    """
    PATCH /api/applications/<id>/status/
    Recruiter updates status → shortlisted / rejected / hired.
    """
    serializer_class   = ApplicationStatusSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Application.objects.filter(job__posted_by=self.request.user)