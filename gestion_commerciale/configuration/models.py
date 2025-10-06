# models.py
from django.db import models

class CompanySettings(models.Model):
    name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to="logos/", null=True, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return "Paramètres de l'entreprise"

    class Meta:
        verbose_name = "Paramètre entreprise"
        verbose_name_plural = "Paramètres entreprise"
