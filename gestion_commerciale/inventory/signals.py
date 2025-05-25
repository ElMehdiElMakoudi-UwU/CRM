from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import StockMovement, Stock, StockAlert
from decimal import Decimal
from decimal import Decimal

@receiver(post_save, sender=StockMovement)
def update_stock_on_movement(sender, instance, created, **kwargs):
    if not created:
        return

    stock, _ = Stock.objects.get_or_create(
        product=instance.product,
        warehouse=instance.warehouse
    )

    # S’assurer que stock.quantity est bien initialisé
    if stock.quantity is None:
        stock.quantity = Decimal('0.00')

    if instance.movement_type == 'in':
        stock.quantity = Decimal(stock.quantity) + Decimal(instance.quantity)
    elif instance.movement_type == 'out':
        stock.quantity = Decimal(stock.quantity) - Decimal(instance.quantity)
    elif instance.movement_type == 'adjustment':
        stock.quantity = Decimal(instance.quantity)

    stock.save()

    if stock.quantity <= stock.reorder_threshold:
        StockAlert.objects.create(
            product=instance.product,
            message=f"Le stock est bas : {stock.quantity} unités restantes.",
        )
