from django.db import migrations

def create_user_profiles(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('users', 'UserProfile')
    
    for user in User.objects.all():
        UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'role': 'sales_rep',  # Default role
                'phone': '',
                'address': ''
            }
        )

def reverse_user_profiles(apps, schema_editor):
    UserProfile = apps.get_model('users', 'UserProfile')
    UserProfile.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_auto_20250606'),
    ]

    operations = [
        migrations.RunPython(create_user_profiles, reverse_user_profiles),
    ] 