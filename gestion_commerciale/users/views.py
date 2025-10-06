from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from .models import UserProfile, ActivityLog
from .forms import UserForm, UserProfileForm
from .decorators import role_required
from django.contrib import messages
from django.contrib.auth.decorators import login_required

@login_required
@role_required(['admin', 'manager'])
def user_list(request):
    users = User.objects.select_related('profile').all()
    return render(request, 'users/user_list.html', {'users': users})

@role_required('admin')
def user_create(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        profile_form = UserProfileForm(request.POST, request.FILES)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()
            return redirect('user_list')
    else:
        user_form = UserForm()
        profile_form = UserProfileForm()
    return render(request, 'users/form.html', {'user_form': user_form, 'profile_form': profile_form})

@role_required('admin')
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    profile = get_object_or_404(UserProfile, user=user)
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect('user_list')
    else:
        user_form = UserForm(instance=user)
        profile_form = UserProfileForm(instance=profile)
    return render(request, 'users/form.html', {'user_form': user_form, 'profile_form': profile_form})

@login_required
@role_required(['admin', 'manager'])
def user_profile(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, instance=request.user.profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            
            ActivityLog.objects.create(
                user=request.user,
                action='update',
                details='Updated profile information'
            )
            
            messages.success(request, 'Votre profil a été mis à jour avec succès!')
            return redirect('users:profile')
    else:
        user_form = UserForm(instance=request.user)
        profile_form = UserProfileForm(instance=request.user.profile)
    
    return render(request, 'users/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })


