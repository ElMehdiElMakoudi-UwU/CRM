# payments/urls.py
from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("clients-dettes/", views.client_debts_list, name="client_debts_list"),
    path("paiement/<int:client_id>/", views.client_payment_create, name="client_payment_create"),
    path("historique/<int:client_id>/", views.client_payment_history, name="client_payment_history"),
    path("export/clients/excel/", views.export_clients_debts_excel, name="export_clients_excel"),
    path("export/client/<int:client_id>/excel/", views.export_client_payments_excel, name="export_client_payments_excel"),
    path("export/clients/pdf/", views.export_clients_debts_pdf, name="export_clients_pdf"),
    path("export/client/<int:client_id>/pdf/", views.export_client_payments_pdf, name="export_client_payments_pdf"),
    path("paiement/<int:payment_id>/annuler/", views.cancel_payment, name="cancel_payment"),
]
