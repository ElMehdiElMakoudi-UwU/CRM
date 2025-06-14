# Generated by Django 4.2.7 on 2025-06-06 20:52

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0005_product_barcode_product_expiration_date_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('mobile_pos', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SalesMetric',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=django.utils.timezone.now)),
                ('total_sales', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('total_orders', models.IntegerField(default=0)),
                ('average_order_value', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
            ],
            options={
                'unique_together': {('date',)},
            },
        ),
        migrations.CreateModel(
            name='SalesRepPerformance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=django.utils.timezone.now)),
                ('orders_processed', models.IntegerField(default=0)),
                ('total_sales', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('conversion_rate', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'date')},
            },
        ),
        migrations.CreateModel(
            name='ProductPerformance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=django.utils.timezone.now)),
                ('units_sold', models.IntegerField(default=0)),
                ('revenue', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='products.product')),
            ],
            options={
                'unique_together': {('product', 'date')},
            },
        ),
    ]
