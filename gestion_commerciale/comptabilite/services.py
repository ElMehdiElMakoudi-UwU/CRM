from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import EcritureComptable, LigneEcriture, ConfigurationComptable

class ComptabiliteService:
    @staticmethod
    def generer_ecriture_vente(vente, user):
        """
        Génère les écritures comptables pour une vente
        :param vente: Instance de Sale
        :param user: Utilisateur qui crée l'écriture
        """
        try:
            config = ConfigurationComptable.objects.first()
            if not config:
                raise ValueError("La configuration comptable n'est pas définie")

            # Calcul des montants
            montant_ht = vente.total_amount / (1 + config.taux_tva / 100)
            montant_tva = vente.total_amount - montant_ht

            with transaction.atomic():
                # Création de l'écriture comptable
                ecriture = EcritureComptable.objects.create(
                    date=vente.date,
                    journal=config.journal_vente,
                    piece=f"VTE{vente.id}",
                    libelle=f"Facture de vente {vente.id} - {vente.client if vente.client else 'Client anonyme'}",
                    created_by=user
                )

                # Ligne client (débit)
                LigneEcriture.objects.create(
                    ecriture=ecriture,
                    compte=config.compte_client,
                    debit=vente.total_amount,
                    credit=0,
                    libelle=f"Facture client {vente.id}"
                )

                # Ligne vente (crédit)
                LigneEcriture.objects.create(
                    ecriture=ecriture,
                    compte=config.compte_vente,
                    debit=0,
                    credit=montant_ht,
                    libelle=f"Vente {vente.id}"
                )

                # Ligne TVA (crédit)
                LigneEcriture.objects.create(
                    ecriture=ecriture,
                    compte=config.compte_tva_collectee,
                    debit=0,
                    credit=montant_tva,
                    libelle=f"TVA sur vente {vente.id}"
                )

                return ecriture

        except Exception as e:
            raise ValueError(f"Erreur lors de la génération de l'écriture comptable : {str(e)}")

    @staticmethod
    def generer_ecriture_paiement(paiement, user):
        """
        Génère les écritures comptables pour un paiement de vente
        :param paiement: Instance de Payment
        :param user: Utilisateur qui crée l'écriture
        """
        # TODO: Implémenter la génération d'écritures pour les paiements
        pass 