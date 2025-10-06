from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import models
from decimal import Decimal

from .models import Sale, SaleItem, Payment
from .services import UnifiedSalesService
from products.models import Product, Category
from clients.models import Client, ClientSegment
from inventory.models import Warehouse, Stock, StockMovement

User = get_user_model()

class SaleTests(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        
        # Create test category
        self.category = Category.objects.create(name="Test Category")
        
        # Create test warehouse
        self.warehouse = Warehouse.objects.create(
            name="Test Warehouse",
            location="Test Location"
        )
        
        # Create test product
        self.product = Product.objects.create(
            name="Test Product",
            reference="TEST001",
            category=self.category,
            purchase_price=Decimal('100.00'),
            selling_price=Decimal('150.00'),
            tax_rate=Decimal('20.00'),
            default_warehouse=self.warehouse
        )
        
        # Create initial stock
        self.stock = Stock.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            quantity=Decimal('100.00')
        )
        
        # Create client segment
        self.segment = ClientSegment.objects.create(
            name="Premium",
            description="Premium clients"
        )
        
        # Create client
        self.client = Client.objects.create(
            name="Test Client",
            segment=self.segment
        )

    def test_sale_creation(self):
        """Test basic sale creation"""
        sale = Sale.objects.create(
            client=self.client,
            warehouse=self.warehouse,
            user=self.user,
            total_amount=Decimal('150.00'),
            amount_paid=Decimal('150.00')
        )
        
        sale_item = SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=Decimal('1.00'),
            unit_price=Decimal('150.00')
        )
        
        self.assertEqual(sale.total_amount, Decimal('150.00'))
        self.assertEqual(sale.amount_paid, Decimal('150.00'))
        self.assertEqual(sale_item.quantity, Decimal('1.00'))

    def test_sale_with_multiple_items(self):
        """Test sale with multiple items"""
        sale = Sale.objects.create(
            client=self.client,
            warehouse=self.warehouse,
            user=self.user,
            total_amount=Decimal('300.00'),
            amount_paid=Decimal('300.00')
        )
        
        # Add two items
        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=Decimal('2.00'),
            unit_price=Decimal('150.00')
        )
        
        # Verify total
        self.assertEqual(sale.total_amount, Decimal('300.00'))
        self.assertEqual(sale.items.count(), 1)
        self.assertEqual(sale.items.first().quantity, Decimal('2.00'))

    def test_stock_update_after_sale(self):
        """Test that stock is properly updated after sale"""
        initial_stock = self.stock.quantity
        
        sale = Sale.objects.create(
            client=self.client,
            warehouse=self.warehouse,
            user=self.user,
            total_amount=Decimal('150.00'),
            amount_paid=Decimal('150.00')
        )
        
        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=Decimal('5.00'),
            unit_price=Decimal('150.00')
        )
        
        # Create stock movement
        StockMovement.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            movement_type='out',
            quantity=Decimal('5.00'),
            source=f"Vente #{sale.id}",
            user=self.user
        )
        
        # Refresh stock from db
        self.stock.refresh_from_db()
        
        # Verify stock was reduced
        self.assertEqual(self.stock.quantity, initial_stock - Decimal('5.00'))

    def test_partial_payment(self):
        """Test sale with partial payment"""
        sale = Sale.objects.create(
            client=self.client,
            warehouse=self.warehouse,
            user=self.user,
            total_amount=Decimal('300.00'),
            amount_paid=Decimal('200.00')
        )
        
        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=Decimal('2.00'),
            unit_price=Decimal('150.00')
        )
        
        Payment.objects.create(
            sale=sale,
            amount=Decimal('200.00'),
            method='cash',
            date=timezone.now()
        )
        
        self.assertEqual(sale.amount_paid, Decimal('200.00'))
        self.assertEqual(sale.get_remaining_amount(), Decimal('100.00'))

    def test_sale_with_tax(self):
        """Test sale with tax calculations"""
        # Product price is 150.00 with 20% tax
        sale = Sale.objects.create(
            client=self.client,
            warehouse=self.warehouse,
            user=self.user,
            total_amount=Decimal('180.00'),  # 150 + 20% TVA
            amount_paid=Decimal('180.00')
        )
        
        sale_item = SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=Decimal('1.00'),
            unit_price=Decimal('150.00')
        )
        
        # Calculate TTC
        price_ttc = sale_item.unit_price * (1 + self.product.tax_rate / 100)
        self.assertEqual(price_ttc, Decimal('180.00'))
        self.assertEqual(sale.total_amount, price_ttc)

    def test_multiple_payments(self):
        """Test multiple payments for a sale"""
        sale = Sale.objects.create(
            client=self.client,
            warehouse=self.warehouse,
            user=self.user,
            total_amount=Decimal('300.00'),
            amount_paid=Decimal('0.00')
        )
        
        # Create two payments
        Payment.objects.create(
            sale=sale,
            amount=Decimal('150.00'),
            method='cash',
            date=timezone.now()
        )
        
        Payment.objects.create(
            sale=sale,
            amount=Decimal('150.00'),
            method='card',
            date=timezone.now()
        )
        
        # Verify payments
        self.assertEqual(sale.amount_paid, Decimal('300.00'))
        self.assertEqual(sale.get_remaining_amount(), Decimal('0.00'))
        self.assertEqual(sale.payments.count(), 2)

    def test_invalid_quantity(self):
        """Test sale with invalid quantity"""
        sale = Sale.objects.create(
            client=self.client,
            warehouse=self.warehouse,
            user=self.user,
            total_amount=Decimal('150.00'),
            amount_paid=Decimal('150.00')
        )
        
        # Try to sell more than available stock
        with self.assertRaises(ValueError):
            SaleItem.objects.create(
                sale=sale,
                product=self.product,
                quantity=Decimal('101.00'),  # Stock is only 100
                unit_price=Decimal('150.00')
            )

    def test_sale_cancellation(self):
        """Test sale cancellation process"""
        # Create sale
        sale = Sale.objects.create(
            client=self.client,
            warehouse=self.warehouse,
            user=self.user,
            total_amount=Decimal('150.00'),
            amount_paid=Decimal('150.00')
        )
        
        initial_stock = self.stock.quantity
        
        sale_item = SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=Decimal('1.00'),
            unit_price=Decimal('150.00')
        )
        
        # Create outgoing stock movement
        StockMovement.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            movement_type='out',
            quantity=Decimal('1.00'),
            source=f"Vente #{sale.id}",
            user=self.user
        )
        
        # Cancel sale
        StockMovement.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            movement_type='in',
            quantity=Decimal('1.00'),
            source=f"Annulation Vente #{sale.id}",
            user=self.user
        )
        
        # Refresh stock
        self.stock.refresh_from_db()
        
        # Verify stock was restored
        self.assertEqual(self.stock.quantity, initial_stock)
