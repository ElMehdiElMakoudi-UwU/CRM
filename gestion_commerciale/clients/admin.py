from django.contrib import admin
from .models import Client, ClientSegment

@admin.register(ClientSegment)
class ClientSegmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'segment', 'balance', 'created_at')
    list_filter = ('segment',)
    search_fields = ('name', 'email', 'phone')
    readonly_fields = ('created_at', 'updated_at')
