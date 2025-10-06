# users/forms.py

from django import forms
from django.contrib.auth.models import User
from .models import UserProfile

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['role', 'phone', 'address']
        labels = {
            'role': 'Rôle',
            'phone': 'Téléphone',
            'address': 'Adresse'
        }
