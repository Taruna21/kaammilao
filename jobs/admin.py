from django.contrib import admin
from .models import Job

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display  = ['title', 'category', 'city', 'pay_amount', 'pay_type', 'status']
    list_filter   = ['category', 'status', 'city']
    search_fields = ['title', 'city', 'area']