# Generated by Django 4.2.7 on 2025-06-08 08:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('comptabilite', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfigurationComptable',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('taux_tva', models.DecimalField(decimal_places=2, default=20.0, max_digits=5)),
                ('compte_client', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='config_client', to='comptabilite.comptecomptable')),
                ('compte_tva_collectee', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='config_tva_collectee', to='comptabilite.comptecomptable')),
                ('compte_vente', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='config_vente', to='comptabilite.comptecomptable')),
                ('journal_vente', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='config_vente', to='comptabilite.journalcomptable')),
            ],
            options={
                'verbose_name': 'Configuration comptable',
                'verbose_name_plural': 'Configurations comptables',
            },
        ),
    ]
