# Generated by Django 4.2.7 on 2025-06-06 21:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0005_product_barcode_product_expiration_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='reorder_threshold',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10, verbose_name='Seuil de réapprovisionnement'),
        ),
    ]
