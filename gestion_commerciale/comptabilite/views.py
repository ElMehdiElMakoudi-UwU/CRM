from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Sum
from .models import (
    CompteComptable,
    JournalComptable,
    EcritureComptable,
    LigneEcriture,
    ExerciceComptable
)

# Create your views here.

class ComptabiliteHomeView(LoginRequiredMixin, ListView):
    template_name = 'comptabilite/home.html'
    model = EcritureComptable
    context_object_name = 'ecritures'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['journaux'] = JournalComptable.objects.all()
        context['exercices'] = ExerciceComptable.objects.filter(cloture=False)
        return context

class CompteComptableListView(LoginRequiredMixin, ListView):
    model = CompteComptable
    template_name = 'comptabilite/compte_list.html'
    context_object_name = 'comptes'
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                models.Q(numero__icontains=search) |
                models.Q(intitule__icontains=search)
            )
        return queryset

class CompteComptableCreateView(LoginRequiredMixin, CreateView):
    model = CompteComptable
    template_name = 'comptabilite/compte_form.html'
    fields = ['numero', 'intitule', 'type', 'parent']
    success_url = reverse_lazy('comptabilite:compte_list')

class EcritureComptableCreateView(LoginRequiredMixin, CreateView):
    model = EcritureComptable
    template_name = 'comptabilite/ecriture_form.html'
    fields = ['date', 'journal', 'piece', 'libelle']
    success_url = reverse_lazy('comptabilite:home')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

class EcritureComptableDetailView(LoginRequiredMixin, DetailView):
    model = EcritureComptable
    template_name = 'comptabilite/ecriture_detail.html'
    context_object_name = 'ecriture'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lignes'] = self.object.lignes.all()
        total_debit = self.object.lignes.aggregate(Sum('debit'))['debit__sum'] or 0
        total_credit = self.object.lignes.aggregate(Sum('credit'))['credit__sum'] or 0
        context['total_debit'] = total_debit
        context['total_credit'] = total_credit
        context['balanced'] = total_debit == total_credit
        return context

class JournalComptableListView(LoginRequiredMixin, ListView):
    model = JournalComptable
    template_name = 'comptabilite/journal_list.html'
    context_object_name = 'journaux'

class ExerciceComptableListView(LoginRequiredMixin, ListView):
    model = ExerciceComptable
    template_name = 'comptabilite/exercice_list.html'
    context_object_name = 'exercices'

class ExerciceComptableCreateView(LoginRequiredMixin, CreateView):
    model = ExerciceComptable
    template_name = 'comptabilite/exercice_form.html'
    fields = ['nom', 'date_debut', 'date_fin']
    success_url = reverse_lazy('comptabilite:exercice_list')

def valider_ecriture(request, pk):
    ecriture = get_object_or_404(EcritureComptable, pk=pk)
    if not ecriture.validated:
        total_debit = ecriture.lignes.aggregate(Sum('debit'))['debit__sum'] or 0
        total_credit = ecriture.lignes.aggregate(Sum('credit'))['credit__sum'] or 0
        
        if total_debit == total_credit:
            ecriture.validate()
            messages.success(request, "L'écriture a été validée avec succès.")
        else:
            messages.error(request, "L'écriture n'est pas équilibrée.")
    return redirect('comptabilite:ecriture_detail', pk=pk)

def cloturer_exercice(request, pk):
    exercice = get_object_or_404(ExerciceComptable, pk=pk)
    if not exercice.cloture:
        # Vérifier que toutes les écritures sont validées
        ecritures_non_validees = EcritureComptable.objects.filter(
            date__range=(exercice.date_debut, exercice.date_fin),
            validated=False
        ).exists()
        
        if not ecritures_non_validees:
            exercice.cloturer()
            messages.success(request, "L'exercice a été clôturé avec succès.")
        else:
            messages.error(request, "Il existe des écritures non validées pour cet exercice.")
    return redirect('comptabilite:exercice_list')
