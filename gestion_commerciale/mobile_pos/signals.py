from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order, SalesMetric, ProductPerformance, SalesRepPerformance

@receiver(post_save, sender=Order)
def calculate_metrics_on_order_save(sender, instance, created, **kwargs):
    """
    Calculate all metrics when an order is created or updated
    """
    # Get the date of the order
    order_date = instance.created_at.date()
    
    # Calculate metrics for that date
    SalesMetric.calculate_metrics(order_date)
    ProductPerformance.calculate_metrics(order_date)
    SalesRepPerformance.calculate_metrics(order_date) 