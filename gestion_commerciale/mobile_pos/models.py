from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from products.models import Product
from datetime import datetime, timedelta

# Create your models here.

class Order(models.Model):
    ORDER_STATUS = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    client_name = models.CharField(max_length=200)
    client_contact = models.CharField(max_length=100)
    order_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.client_name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity}x {self.product.name} in Order #{self.order.id}"

class SalesMetric(models.Model):
    date = models.DateField(default=timezone.now)
    total_sales = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_orders = models.IntegerField(default=0)
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ['date']
        
    @classmethod
    def calculate_metrics(cls, date=None):
        if date is None:
            date = timezone.now().date()
            
        orders = Order.objects.filter(created_at__date=date)
        total_sales = orders.aggregate(total=models.Sum('total_amount'))['total'] or 0
        total_orders = orders.count()
        avg_order = total_sales / total_orders if total_orders > 0 else 0
        
        metric, _ = cls.objects.update_or_create(
            date=date,
            defaults={
                'total_sales': total_sales,
                'total_orders': total_orders,
                'average_order_value': avg_order
            }
        )
        return metric

class ProductPerformance(models.Model):
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    units_sold = models.IntegerField(default=0)
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ['product', 'date']
        
    @classmethod
    def calculate_metrics(cls, date=None):
        if date is None:
            date = timezone.now().date()
            
        # Get all order items for the day
        items = OrderItem.objects.filter(
            order__created_at__date=date
        ).values('product').annotate(
            daily_units=models.Sum('quantity'),
            daily_revenue=models.Sum(models.F('quantity') * models.F('price'))
        )
        
        # Update or create performance records
        for item in items:
            cls.objects.update_or_create(
                product_id=item['product'],
                date=date,
                defaults={
                    'units_sold': item['daily_units'],
                    'revenue': item['daily_revenue']
                }
            )

class SalesRepPerformance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    orders_processed = models.IntegerField(default=0)
    total_sales = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # in percentage
    
    class Meta:
        unique_together = ['user', 'date']
        
    @classmethod
    def calculate_metrics(cls, date=None):
        if date is None:
            date = timezone.now().date()
            
        # Calculate metrics for each sales rep
        for user in User.objects.filter(is_staff=True):
            orders = Order.objects.filter(
                created_at__date=date,
                created_by=user
            )
            
            total_sales = orders.aggregate(total=models.Sum('total_amount'))['total'] or 0
            orders_processed = orders.count()
            
            # Assuming we track order views/attempts somewhere
            # conversion_rate = (orders_processed / order_attempts) * 100 if order_attempts > 0 else 0
            conversion_rate = 0  # We'll implement this later
            
            cls.objects.update_or_create(
                user=user,
                date=date,
                defaults={
                    'orders_processed': orders_processed,
                    'total_sales': total_sales,
                    'conversion_rate': conversion_rate
                }
            )
