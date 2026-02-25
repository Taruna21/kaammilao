from django.contrib import admin
from .models import Application

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display  = ['applicant', 'job', 'status', 'applied_at']
    list_filter   = ['status']