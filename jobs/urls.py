from django.urls import path
from . import views

urlpatterns = [
    path('',        views.JobListView.as_view(),   name='job-list'),
    path('create/', views.JobCreateView.as_view(), name='job-create'),
    path('mine/',   views.MyJobsView.as_view(),    name='my-jobs'),
    path('<int:pk>/', views.JobDetailView.as_view(), name='job-detail'),
]