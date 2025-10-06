from django.db import models
from django.utils import timezone
from django.conf import settings

class CompteComptable(models.Model):
    """Plan comptable"""
    numero = models.CharField(max_length=10, unique=True)
    intitule = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=[
        ('actif', 'Actif'),
        ('passif', 'Passif'),
        ('charge', 'Charge'),
        ('produit', 'Produit'),
    ])
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='sous_comptes')

    class Meta:
        ordering = ['numero']
        verbose_name = "Compte comptable"
        verbose_name_plural = "Plan comptable"

    def __str__(self):
        return f"{self.numero} - {self.intitule}"

class JournalComptable(models.Model):
    """Journal comptable"""
    code = models.CharField(max_length=10, unique=True)
    nom = models.CharField(max_length=100)
    type = models.CharField(max_length=50, choices=[
        ('achat', 'Achats'),
        ('vente', 'Ventes'),
        ('banque', 'Banque'),
        ('caisse', 'Caisse'),
        ('operation', 'Opérations diverses'),
    ])

    class Meta:
        verbose_name = "Journal comptable"
        verbose_name_plural = "Journaux comptables"

    def __str__(self):
        return f"{self.code} - {self.nom}"

class EcritureComptable(models.Model):
    """Écriture comptable"""
    date = models.DateField(default=timezone.now)
    journal = models.ForeignKey(JournalComptable, on_delete=models.PROTECT)
    piece = models.CharField(max_length=50, help_text="Numéro de pièce justificative")
    libelle = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    validated = models.BooleanField(default=False)
    validation_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Écriture comptable"
        verbose_name_plural = "Écritures comptables"
        ordering = ['-date', '-id']

    def __str__(self):
        return f"{self.date} - {self.piece} - {self.libelle}"

    def validate(self):
        """Valider l'écriture comptable"""
        if not self.validated:
            self.validated = True
            self.validation_date = timezone.now()
            self.save()

class LigneEcriture(models.Model):
    """Ligne d'écriture comptable"""
    ecriture = models.ForeignKey(EcritureComptable, on_delete=models.CASCADE, related_name='lignes')
    compte = models.ForeignKey(CompteComptable, on_delete=models.PROTECT)
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    libelle = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Ligne d'écriture"
        verbose_name_plural = "Lignes d'écritures"

    def __str__(self):
        return f"{self.compte} - {'Débit' if self.debit > 0 else 'Crédit'} : {self.debit or self.credit}"

class ExerciceComptable(models.Model):
    """Exercice comptable"""
    nom = models.CharField(max_length=100)
    date_debut = models.DateField()
    date_fin = models.DateField()
    cloture = models.BooleanField(default=False)
    date_cloture = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Exercice comptable"
        verbose_name_plural = "Exercices comptables"
        ordering = ['-date_debut']

    def __str__(self):
        return self.nom

    def cloturer(self):
        """Clôturer l'exercice comptable"""
        if not self.cloture:
            self.cloture = True
            self.date_cloture = timezone.now()
            self.save()

class ConfigurationComptable(models.Model):
    """Configuration des comptes par défaut"""
    compte_client = models.ForeignKey(CompteComptable, on_delete=models.PROTECT, related_name='config_client')
    compte_vente = models.ForeignKey(CompteComptable, on_delete=models.PROTECT, related_name='config_vente')
    compte_tva_collectee = models.ForeignKey(CompteComptable, on_delete=models.PROTECT, related_name='config_tva_collectee')
    journal_vente = models.ForeignKey(JournalComptable, on_delete=models.PROTECT, related_name='config_vente')
    taux_tva = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)
    
    class Meta:
        verbose_name = "Configuration comptable"
        verbose_name_plural = "Configurations comptables"

    def __str__(self):
        return "Configuration comptable globale"

    def save(self, *args, **kwargs):
        if not self.pk and ConfigurationComptable.objects.exists():
            # S'assurer qu'il n'y a qu'une seule configuration
            return
        return super().save(*args, **kwargs)
