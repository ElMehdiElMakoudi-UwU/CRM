from django.db import models
from django.contrib.auth import get_user_model

class ClientSegment(models.Model):
    """
    Catégorie ou segment marketing/commercial pour regrouper les clients par comportement ou caractéristiques.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Client(models.Model):

    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    # Segmentation
    segment = models.ForeignKey(ClientSegment, on_delete=models.SET_NULL, null=True, blank=True, related_name='clients')

    # Solde du client (positif si le client nous doit de l'argent, négatif si nous lui devons)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    alert_threshold = models.DecimalField(max_digits=10,decimal_places=2,default=5000.00,verbose_name="Seuil d'alerte de solde")
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True, related_name='created_clients')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']