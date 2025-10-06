from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import StockMovement, Stock, StockAlert
from decimal import Decimal

@receiver(post_save, sender=StockMovement)
def update_stock_on_movement(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.movement_type == 'transfer':
        # Gérer le transfert entre entrepôts
        from_stock, _ = Stock.objects.get_or_create(
            product=instance.product,
            warehouse=instance.from_warehouse,
            defaults={'quantity': Decimal('0.00')}
        )
        to_stock, _ = Stock.objects.get_or_create(
            product=instance.product,
            warehouse=instance.to_warehouse,
            defaults={'quantity': Decimal('0.00')}
        )
        
        from_stock.quantity = Decimal(from_stock.quantity) - Decimal(instance.quantity)
        to_stock.quantity = Decimal(to_stock.quantity) + Decimal(instance.quantity)
        
        from_stock.save()
        to_stock.save()
        
        # Vérifier les seuils pour les deux entrepôts
        if from_stock.quantity <= from_stock.product.reorder_threshold:
            StockAlert.objects.create(
                product=instance.product,
                warehouse=instance.from_warehouse,
                message=f"Le stock est bas : {from_stock.quantity} unités restantes.",
                is_resolved=False
            )
        if to_stock.quantity <= to_stock.product.reorder_threshold:
            StockAlert.objects.create(
                product=instance.product,
                warehouse=instance.to_warehouse,
                message=f"Le stock est bas : {to_stock.quantity} unités restantes.",
                is_resolved=False
            )
    else:
        # Gérer les autres types de mouvements (entrée, sortie, ajustement)
        stock, _ = Stock.objects.get_or_create(
            product=instance.product,
            warehouse=instance.warehouse,
            defaults={'quantity': Decimal('0.00')}
        )

        if instance.movement_type == 'in':
            stock.quantity = Decimal(stock.quantity) + Decimal(instance.quantity)
        elif instance.movement_type == 'out':
            stock.quantity = Decimal(stock.quantity) - Decimal(instance.quantity)
        elif instance.movement_type == 'adjustment':
            stock.quantity = Decimal(instance.quantity)

        stock.save()

        # Vérifier le seuil
        if stock.quantity <= stock.product.reorder_threshold:
            StockAlert.objects.create(
                product=instance.product,
                warehouse=instance.warehouse,
                message=f"Le stock est bas : {stock.quantity} unités restantes.",
                is_resolved=False
            )
