from django.contrib import admin
from .models import (
    CompteComptable,
    JournalComptable,
    EcritureComptable,
    LigneEcriture,
    ExerciceComptable,
    ConfigurationComptable
)

class LigneEcritureInline(admin.TabularInline):
    model = LigneEcriture
    extra = 0
    fields = ['compte', 'debit', 'credit', 'libelle']

@admin.register(CompteComptable)
class CompteComptableAdmin(admin.ModelAdmin):
    list_display = ['numero', 'intitule', 'type']
    list_filter = ['type']
    search_fields = ['numero', 'intitule']

@admin.register(JournalComptable)
class JournalComptableAdmin(admin.ModelAdmin):
    list_display = ['code', 'nom', 'type']
    list_filter = ['type']
    search_fields = ['code', 'nom']

@admin.register(EcritureComptable)
class EcritureComptableAdmin(admin.ModelAdmin):
    list_display = ['date', 'journal', 'piece', 'libelle', 'created_by', 'validated']
    list_filter = ['journal', 'validated', 'date']
    search_fields = ['piece', 'libelle']
    inlines = [LigneEcritureInline]
    readonly_fields = ['created_at', 'created_by', 'validated', 'validation_date']

@admin.register(ExerciceComptable)
class ExerciceComptableAdmin(admin.ModelAdmin):
    list_display = ['nom', 'date_debut', 'date_fin', 'cloture']
    list_filter = ['cloture']
    search_fields = ['nom']

@admin.register(ConfigurationComptable)
class ConfigurationComptableAdmin(admin.ModelAdmin):
    list_display = ['compte_client', 'compte_vente', 'compte_tva_collectee', 'journal_vente', 'taux_tva']
    
    def has_add_permission(self, request):
        # Ne permet pas d'ajouter si une configuration existe déjà
        return not ConfigurationComptable.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Ne permet pas de supprimer la configuration
        return False
