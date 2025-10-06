from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import PriceGrid, PriceRule
from .forms import PriceGridForm, PriceRuleForm

@login_required
def price_grid_list(request):
    """
    Liste des grilles tarifaires
    """
    grids = PriceGrid.objects.all()
    return render(request, 'pricing/price_grid_list.html', {
        'grids': grids
    })

@login_required
def price_grid_detail(request, pk):
    """
    Détails d'une grille tarifaire
    """
    grid = get_object_or_404(PriceGrid, pk=pk)
    return render(request, 'pricing/price_grid_detail.html', {
        'grid': grid
    })

@login_required
def price_grid_create(request):
    """
    Création d'une grille tarifaire
    """
    if request.method == 'POST':
        form = PriceGridForm(request.POST)
        if form.is_valid():
            grid = form.save()
            messages.success(request, 'Grille tarifaire créée avec succès.')
            return redirect('pricing:price_grid_detail', pk=grid.pk)
    else:
        form = PriceGridForm()
    
    return render(request, 'pricing/price_grid_form.html', {
        'form': form,
        'title': 'Nouvelle grille tarifaire'
    })

@login_required
def price_grid_update(request, pk):
    """
    Modification d'une grille tarifaire
    """
    grid = get_object_or_404(PriceGrid, pk=pk)
    
    if request.method == 'POST':
        form = PriceGridForm(request.POST, instance=grid)
        if form.is_valid():
            form.save()
            messages.success(request, 'Grille tarifaire mise à jour avec succès.')
            return redirect('pricing:price_grid_detail', pk=grid.pk)
    else:
        form = PriceGridForm(instance=grid)
    
    return render(request, 'pricing/price_grid_form.html', {
        'form': form,
        'grid': grid,
        'title': 'Modifier la grille tarifaire'
    })

@login_required
def price_rule_create(request, grid_pk):
    """
    Ajout d'une règle de prix à une grille tarifaire
    """
    grid = get_object_or_404(PriceGrid, pk=grid_pk)
    
    if request.method == 'POST':
        form = PriceRuleForm(request.POST)
        if form.is_valid():
            rule = form.save(commit=False)
            rule.price_grid = grid
            rule.save()
            messages.success(request, 'Règle de prix ajoutée avec succès.')
            return redirect('pricing:price_grid_detail', pk=grid.pk)
    else:
        form = PriceRuleForm()
    
    return render(request, 'pricing/price_rule_form.html', {
        'form': form,
        'grid': grid,
        'title': 'Nouvelle règle de prix'
    })

@login_required
def price_rule_update(request, pk):
    """
    Modification d'une règle de prix
    """
    rule = get_object_or_404(PriceRule, pk=pk)
    
    if request.method == 'POST':
        form = PriceRuleForm(request.POST, instance=rule)
        if form.is_valid():
            form.save()
            messages.success(request, 'Règle de prix mise à jour avec succès.')
            return redirect('pricing:price_grid_detail', pk=rule.price_grid.pk)
    else:
        form = PriceRuleForm(instance=rule)
    
    return render(request, 'pricing/price_rule_form.html', {
        'form': form,
        'rule': rule,
        'grid': rule.price_grid,
        'title': 'Modifier la règle de prix'
    })

@login_required
def price_rule_delete(request, pk):
    """
    Suppression d'une règle de prix
    """
    rule = get_object_or_404(PriceRule, pk=pk)
    grid_pk = rule.price_grid.pk
    
    if request.method == 'POST':
        rule.delete()
        messages.success(request, 'Règle de prix supprimée avec succès.')
        return redirect('pricing:price_grid_detail', pk=grid_pk)
    
    return render(request, 'pricing/price_rule_confirm_delete.html', {
        'rule': rule
    }) 