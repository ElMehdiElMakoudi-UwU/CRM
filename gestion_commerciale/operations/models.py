from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Seller(models.Model):
    """Represents a mobile seller or sales representative."""
    name = models.CharField(max_length=150, unique=True)
    # Optionally link to a User
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='seller_profile')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class SellerProductDayEntry(models.Model):
    """
    Tracks inventory movements (load, return, sales) for a specific
    Product, Seller, and Date.
    """
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name='daily_entries')
    # Use string reference to the Product model in the 'products' app
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='seller_daily_entries')
    date = models.DateField()

    # Inventory fields
    voiture = models.DecimalField("Stock Précédent (Voiture)", max_digits=10, decimal_places=2, default=0.00)
    sortie = models.DecimalField("Sortie (Chargement)", max_digits=10, decimal_places=2, default=0.00)
    retour = models.DecimalField("Retour (Déchargement)", max_digits=10, decimal_places=2, default=0.00)

    # Calculated fields
    total_loaded = models.DecimalField("Total Chargé", max_digits=10, decimal_places=2, default=0.00) # voiture + sortie
    vendu = models.DecimalField("Vendu", max_digits=10, decimal_places=2, default=0.00)
    amount = models.DecimalField("Montant Vendu", max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ('seller', 'product', 'date')
        verbose_name = "Entrée Quotidienne Vendeur/Produit"
        verbose_name_plural = "Entrées Quotidiennes Vendeur/Produit"

    def __str__(self):
        return f"{self.seller.name} - {self.product.name} ({self.date})"
