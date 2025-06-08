from django.urls import path
from . import views

app_name = 'comptabilite'

urlpatterns = [
    # Page d'accueil de la comptabilité
    path('', views.ComptabiliteHomeView.as_view(), name='home'),

    # Gestion des comptes comptables
    path('comptes/', views.CompteComptableListView.as_view(), name='compte_list'),
    path('comptes/nouveau/', views.CompteComptableCreateView.as_view(), name='compte_create'),

    # Gestion des écritures comptables
    path('ecritures/nouvelle/', views.EcritureComptableCreateView.as_view(), name='ecriture_create'),
    path('ecritures/<int:pk>/', views.EcritureComptableDetailView.as_view(), name='ecriture_detail'),
    path('ecritures/<int:pk>/valider/', views.valider_ecriture, name='ecriture_validate'),

    # Gestion des journaux comptables
    path('journaux/', views.JournalComptableListView.as_view(), name='journal_list'),

    # Gestion des exercices comptables
    path('exercices/', views.ExerciceComptableListView.as_view(), name='exercice_list'),
    path('exercices/nouveau/', views.ExerciceComptableCreateView.as_view(), name='exercice_create'),
    path('exercices/<int:pk>/cloturer/', views.cloturer_exercice, name='exercice_cloturer'),
] 