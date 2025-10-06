# payments/admin.py
from django.contrib import admin
from .models import ClientPayment

@admin.register(ClientPayment)
class ClientPaymentAdmin(admin.ModelAdmin):
    list_display = ['client', 'amount', 'method', 'date', 'user']
    list_filter = ['method', 'date', 'client']
    search_fields = ['client__name']
