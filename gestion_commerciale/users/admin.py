# users/admin.py

from django.contrib import admin
from .models import UserProfile, ActivityLog

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'active')

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'target_type', 'target_id')
    list_filter = ('user', 'target_type')
    search_fields = ('action',)
