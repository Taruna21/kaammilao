from django.urls import path
from . import views

urlpatterns = [
    path('',                                           views.seeker_dashboard,          name='seeker_dashboard'),
    path('<int:job_id>/',                              views.job_detail,                name='job_detail'),
    path('apply/<int:job_id>/',                        views.apply_to_job,              name='apply_to_job'),
    path('my-applications/',                           views.my_applications,           name='my_applications'),
    path('recruiter/',                                 views.recruiter_dashboard,       name='recruiter_dashboard'),
    path('recruiter/post/',                            views.post_job,                  name='post_job'),
    path('recruiter/edit/<int:job_id>/',               views.edit_job,                  name='edit_job'),
    path('recruiter/toggle/<int:job_id>/',             views.toggle_job_status,         name='toggle_job_status'),
    path('recruiter/applicants/<int:job_id>/',         views.job_applicants,            name='job_applicants'),
    path('recruiter/delete/<int:job_id>/',             views.delete_job,                name='delete_job'),
    path('recruiter/application/<int:app_id>/status/', views.update_application_status, name='update_application_status'),
]
