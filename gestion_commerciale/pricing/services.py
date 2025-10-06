from datetime import date
from typing import Optional
from decimal import Decimal
from django.db.models import Q
from .models import PriceGrid, PriceRule
from clients.models import Client, ClientSegment
from products.models import Product

class PricingService:
    @staticmethod
    def get_price_for_client(client: Client, product: Product, quantity: int = 1) -> Decimal:
        """
        Calcule le prix d'un produit pour un client spécifique en tenant compte des grilles tarifaires
        """
        if not client.segment:
            return product.selling_price

        # Chercher les règles de prix applicables
        today = date.today()
        price_rules = PriceRule.objects.filter(
            price_grid__segment=client.segment,
            price_grid__is_active=True,
            product=product,
            is_active=True,
            min_quantity__lte=quantity
        ).filter(
            (Q(start_date__isnull=True) | Q(start_date__lte=today)) &
            (Q(end_date__isnull=True) | Q(end_date__gte=today))
        )

        # Trouver la règle qui donne le prix le plus avantageux
        best_price = product.selling_price
        best_rule = None

        for rule in price_rules:
            price = rule.get_final_price(product.selling_price)
            if price < best_price:
                best_price = price
                best_rule = rule

        return best_price if best_rule else product.selling_price

    @staticmethod
    def get_bulk_prices_for_client(client: Client, products: list[Product]) -> dict[int, Decimal]:
        """
        Calcule les prix pour une liste de produits pour un client spécifique
        """
        prices = {}
        for product in products:
            prices[product.id] = PricingService.get_price_for_client(client, product)
        return prices

    @staticmethod
    def get_available_price_grids(client: Optional[Client] = None, 
                                segment: Optional[ClientSegment] = None) -> list[PriceGrid]:
        """
        Retourne les grilles tarifaires disponibles pour un client ou un segment
        """
        if client and client.segment:
            segment = client.segment
        
        if segment:
            return PriceGrid.objects.filter(
                segment=segment,
                is_active=True
            )
        return PriceGrid.objects.filter(is_active=True) 