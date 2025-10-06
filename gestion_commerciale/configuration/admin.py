# admin.py
from django.contrib import admin
from .models import CompanySettings

@admin.register(CompanySettings)
class CompanySettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Limite à un seul enregistrement
        return not CompanySettings.objects.exists()
