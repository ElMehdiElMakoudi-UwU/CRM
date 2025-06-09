from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def sum_attr(queryset, attr):
    """
    Calcule la somme d'un attribut donné pour une liste d'objets.
    Usage: {{ entries|sum_attr:'sold_quantity' }}
    """
    try:
        return sum(Decimal(str(getattr(obj, attr, 0))) for obj in queryset)
    except (TypeError, ValueError):
        return Decimal('0')

@register.filter
def startswith(text, starts):
    """
    Vérifie si une chaîne commence par une sous-chaîne donnée.
    Usage: {{ field.name|startswith:'return_' }}
    """
    if text:
        return str(text).startswith(str(starts))
    return False 