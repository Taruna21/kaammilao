from django.urls import path
from . import views

urlpatterns = [
    path('apply/',               views.ApplyToJobView.as_view(),          name='apply'),
    path('mine/',                views.MyApplicationsView.as_view(),       name='my-applications'),
    path('job/<int:job_id>/',    views.JobApplicationsView.as_view(),      name='job-applications'),
    path('<int:pk>/status/',     views.UpdateApplicationStatusView.as_view(), name='update-status'),
]