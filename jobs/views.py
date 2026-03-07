from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from rest_framework import generics, permissions, filters
from rest_framework.response import Response
from .models import Job
from .serializers import JobSerializer, JobCreateSerializer
from applications.models import Application
from users.notifications import notify_new_application, notify_status_update


def redirect_if_wrong_role(user, required_role):
    return user.role != required_role


@login_required
def seeker_dashboard(request):
    if redirect_if_wrong_role(request.user, 'seeker'):
        messages.error(request, 'This page is for job seekers only.')
        return redirect('recruiter_dashboard')

    jobs     = Job.objects.filter(status='open').select_related('posted_by')
    city     = request.GET.get('city', '').strip()
    category = request.GET.get('category', '')

    if city:     jobs = jobs.filter(city__icontains=city)
    if category: jobs = jobs.filter(category=category)

    applied_job_ids = list(
        Application.objects.filter(
            applicant=request.user
        ).values_list('job_id', flat=True)
    )

    my_applications = Application.objects.filter(
        applicant=request.user
    ).select_related('job').order_by('-applied_at')

    return render(request, 'jobs/seeker_dashboard.html', {
        'jobs':            jobs,
        'city':            city,
        'category':        category,
        'applied_job_ids': applied_job_ids,
        'my_applications': my_applications,
        'categories':      Job.CATEGORY_CHOICES,
    })


@login_required
def apply_to_job(request, job_id):
    if redirect_if_wrong_role(request.user, 'seeker'):
        messages.error(request, 'Only job seekers can apply.')
        return redirect('recruiter_dashboard')

    job = get_object_or_404(Job, id=job_id, status='open')

    # Check already applied
    if Application.objects.filter(job=job, applicant=request.user).exists():
        messages.info(request, 'You already applied to this job.')
        return redirect('seeker_dashboard')

    if request.method == 'POST':
        name       = request.POST.get('name', '').strip()
        phone      = request.POST.get('phone', '').strip()
        city       = request.POST.get('city', '').strip()
        cover_note = request.POST.get('cover_note', '').strip()

        if not name or not phone:
            messages.error(request, 'Name and phone number are required.')
            return render(request, 'jobs/apply_form.html', {
                'job':  job,
                'form_data': request.POST,
            })

        app = Application.objects.create(
            job             = job,
            applicant       = request.user,
            applicant_name  = name,
            applicant_phone = phone,
            applicant_city  = city,
            cover_note      = cover_note,
        )
        # Notify recruiter
        notify_new_application(job, app)
        messages.success(request, f'Applied to "{job.title}" successfully!')
        return redirect('seeker_dashboard')

    # GET — show the apply form
    return render(request, 'jobs/apply_form.html', {
        'job': job,
        'form_data': {
            'name':  request.user.full_name,
            'phone': request.user.phone,
            'city':  request.user.city,
        }
    })

@login_required
def my_applications(request):
    apps = Application.objects.filter(
        applicant=request.user
    ).select_related('job', 'job__posted_by').order_by('-applied_at')
    return render(request, 'jobs/my_applications.html', {'applications': apps})


@login_required
def recruiter_dashboard(request):
    if redirect_if_wrong_role(request.user, 'recruiter'):
        messages.error(request, 'This page is for recruiters only.')
        return redirect('seeker_dashboard')

    jobs = Job.objects.filter(
        posted_by=request.user
    ).order_by('-created_at')

    # Count applications per job
    for job in jobs:
        job.application_count = Application.objects.filter(job=job).count()

    return render(request, 'jobs/recruiter_dashboard.html', {'jobs': jobs})


@login_required
def post_job(request):
    if redirect_if_wrong_role(request.user, 'recruiter'):
        messages.error(request, 'Only recruiters can post jobs.')
        return redirect('seeker_dashboard')

    if request.method == 'POST':
        title      = request.POST.get('title', '').strip()
        category   = request.POST.get('category', '')
        city       = request.POST.get('city', '').strip()
        area       = request.POST.get('area', '').strip()
        pincode    = request.POST.get('pincode', '').strip()
        pay_amount = request.POST.get('pay_amount', '')
        pay_type   = request.POST.get('pay_type', 'daily')
        description = request.POST.get('description', '').strip()

        if not title or not category or not city or not pay_amount:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'jobs/post_job.html', {
                'categories':      Job.CATEGORY_CHOICES,
                'pay_type_choices': Job.PAY_TYPE_CHOICES,
                'form_data':        request.POST,
            })

        Job.objects.create(
            posted_by   = request.user,
            title       = title,
            category    = category,
            description = description,
            city        = city,
            area        = area,
            pincode     = pincode,
            pay_amount  = pay_amount,
            pay_type    = pay_type,
        )
        messages.success(request, f'"{title}" posted successfully!')
        return redirect('recruiter_dashboard')

    return render(request, 'jobs/post_job.html', {
        'categories':       Job.CATEGORY_CHOICES,
        'pay_type_choices': Job.PAY_TYPE_CHOICES,
    })


@login_required
def job_applicants(request, job_id):
    if redirect_if_wrong_role(request.user, 'recruiter'):
        return redirect('seeker_dashboard')

    job  = get_object_or_404(Job, id=job_id, posted_by=request.user)
    apps = Application.objects.filter(job=job).select_related('applicant')

    return render(request, 'jobs/job_applicants.html', {
        'job':          job,
        'applications': apps,
    })

@login_required
def job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    already_applied = Application.objects.filter(
        job=job, applicant=request.user
    ).exists()
    return render(request, 'jobs/job_detail.html', {
        'job':            job,
        'already_applied': already_applied,
    })

@login_required
def update_application_status(request, app_id):
    if request.method == 'POST':
        app    = get_object_or_404(Application, id=app_id, job__posted_by=request.user)
        status = request.POST.get('status')
        if status in ['pending', 'shortlisted', 'rejected', 'hired']:
            app.status = status
            app.save()
            # Notify seeker
            notify_status_update(app)
            messages.success(request, f'Application marked as {status}.')
    return redirect('job_applicants', job_id=app.job.id)


@login_required
def delete_job(request, job_id):
    job = get_object_or_404(Job, id=job_id, posted_by=request.user)
    job.delete()
    messages.success(request, f'"{job.title}" deleted.')
    return redirect('recruiter_dashboard')


class JobListView(generics.ListAPIView):
    serializer_class   = JobSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends    = [filters.SearchFilter]
    search_fields      = ['title', 'city', 'area', 'category']

    def get_queryset(self):
        queryset = Job.objects.filter(status='open')
        city     = self.request.query_params.get('city')
        category = self.request.query_params.get('category')
        if city:     queryset = queryset.filter(city__icontains=city)
        if category: queryset = queryset.filter(category=category)
        return queryset


class JobCreateView(generics.CreateAPIView):
    serializer_class   = JobCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(posted_by=self.request.user)


class JobDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class   = JobSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return Job.objects.all()

    def update(self, request, *args, **kwargs):
        job = self.get_object()
        if job.posted_by != request.user:
            return Response({'error': 'You can only edit your own jobs'}, status=403)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        job = self.get_object()
        if job.posted_by != request.user:
            return Response({'error': 'You can only delete your own jobs'}, status=403)
        return super().destroy(request, *args, **kwargs)


class MyJobsView(generics.ListAPIView):
    serializer_class   = JobSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Job.objects.filter(posted_by=self.request.user)

@login_required
def edit_job(request, job_id):
    from .models import Job
    job = get_object_or_404(Job, id=job_id, posted_by=request.user)
    if request.method == 'POST':
        job.title       = request.POST.get('title', job.title).strip()
        job.city        = request.POST.get('city', job.city).strip()
        job.area        = request.POST.get('area', '').strip()
        job.pay_amount  = request.POST.get('pay_amount', job.pay_amount)
        job.pay_type    = request.POST.get('pay_type', job.pay_type)
        job.description = request.POST.get('description', '').strip()
        job.save()
        messages.success(request, 'Job updated!')
    return redirect('recruiter_dashboard')


@login_required
def toggle_job_status(request, job_id):
    from .models import Job
    job = get_object_or_404(Job, id=job_id, posted_by=request.user)
    if request.method == 'POST':
        job.status = 'closed' if job.status == 'open' else 'open'
        job.save()
    return redirect('recruiter_dashboard')
