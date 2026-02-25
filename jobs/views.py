from rest_framework import generics, permissions, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Job
from .serializers import JobSerializer, JobCreateSerializer


class JobListView(generics.ListAPIView):
    """
    GET /api/jobs/
    Returns all open jobs. Supports filtering by city & category.
    """
    serializer_class   = JobSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends    = [filters.SearchFilter]
    search_fields      = ['title', 'city', 'area', 'category']

    def get_queryset(self):
        queryset = Job.objects.filter(status='open')

        # Filter by city if provided: /api/jobs/?city=Dehradun
        city = self.request.query_params.get('city')
        if city:
            queryset = queryset.filter(city__icontains=city)

        # Filter by category: /api/jobs/?category=plumber
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        return queryset


class JobCreateView(generics.CreateAPIView):
    """
    POST /api/jobs/create/
    Only logged-in recruiters can post jobs.
    """
    serializer_class   = JobCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(posted_by=self.request.user)


class JobDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/jobs/<id>/   → view job
    PUT    /api/jobs/<id>/   → edit job (recruiter only)
    DELETE /api/jobs/<id>/   → delete job (recruiter only)
    """
    serializer_class   = JobSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return Job.objects.all()

    def update(self, request, *args, **kwargs):
        job = self.get_object()
        # Only the recruiter who posted it can edit
        if job.posted_by != request.user:
            return Response({'error': 'You can only edit your own jobs'}, status=403)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        job = self.get_object()
        if job.posted_by != request.user:
            return Response({'error': 'You can only delete your own jobs'}, status=403)
        return super().destroy(request, *args, **kwargs)


class MyJobsView(generics.ListAPIView):
    """
    GET /api/jobs/mine/
    Recruiter sees only their posted jobs.
    """
    serializer_class   = JobSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Job.objects.filter(posted_by=self.request.user)