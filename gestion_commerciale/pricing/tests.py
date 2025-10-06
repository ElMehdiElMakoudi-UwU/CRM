from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta

from .models import PriceGrid, PriceRule
from .services import PricingService
from clients.models import Client, ClientSegment
from products.models import Product, Category

class PriceGridTests(TestCase):
    def setUp(self):
        # Create test category
        self.category = Category.objects.create(name="Test Category")
        
        # Create test product
        self.product = Product.objects.create(
            name="Test Product",
            reference="TEST001",
            category=self.category,
            purchase_price=Decimal('100.00'),
            selling_price=Decimal('150.00'),
            tax_rate=Decimal('20.00')
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
        
        # Create price grid
        self.price_grid = PriceGrid.objects.create(
            name="Test Grid",
            segment=self.segment,
            is_active=True
        )

    def test_price_grid_creation(self):
        """Test that price grid is created correctly"""
        self.assertEqual(self.price_grid.name, "Test Grid")
        self.assertEqual(self.price_grid.segment, self.segment)
        self.assertTrue(self.price_grid.is_active)

    def test_price_rule_percentage_discount(self):
        """Test percentage discount calculation"""
        rule = PriceRule.objects.create(
            price_grid=self.price_grid,
            product=self.product,
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_quantity=1,
            is_active=True
        )
        
        # Calculate price (should be 150 - 10% = 135)
        price = PricingService.get_price_for_client(self.client, self.product)
        self.assertEqual(price, Decimal('135.00'))

    def test_price_rule_fixed_discount(self):
        """Test fixed amount discount calculation"""
        rule = PriceRule.objects.create(
            price_grid=self.price_grid,
            product=self.product,
            discount_type='fixed',
            discount_value=Decimal('20.00'),
            min_quantity=1,
            is_active=True
        )
        
        # Calculate price (should be 150 - 20 = 130)
        price = PricingService.get_price_for_client(self.client, self.product)
        self.assertEqual(price, Decimal('130.00'))

    def test_price_rule_fixed_price(self):
        """Test fixed price rule"""
        rule = PriceRule.objects.create(
            price_grid=self.price_grid,
            product=self.product,
            discount_type='fixed_price',
            discount_value=Decimal('125.00'),
            min_quantity=1,
            is_active=True
        )
        
        # Calculate price (should be exactly 125)
        price = PricingService.get_price_for_client(self.client, self.product)
        self.assertEqual(price, Decimal('125.00'))

    def test_quantity_based_pricing(self):
        """Test quantity-based pricing rules"""
        # Create two rules with different quantities
        PriceRule.objects.create(
            price_grid=self.price_grid,
            product=self.product,
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_quantity=1,
            is_active=True
        )
        
        PriceRule.objects.create(
            price_grid=self.price_grid,
            product=self.product,
            discount_type='percentage',
            discount_value=Decimal('20.00'),
            min_quantity=5,
            is_active=True
        )
        
        # Test price for quantity = 1 (should be 150 - 10% = 135)
        price1 = PricingService.get_price_for_client(self.client, self.product, quantity=1)
        self.assertEqual(price1, Decimal('135.00'))
        
        # Test price for quantity = 5 (should be 150 - 20% = 120)
        price5 = PricingService.get_price_for_client(self.client, self.product, quantity=5)
        self.assertEqual(price5, Decimal('120.00'))

    def test_date_range_pricing(self):
        """Test date-range based pricing rules"""
        today = date.today()
        
        rule = PriceRule.objects.create(
            price_grid=self.price_grid,
            product=self.product,
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_quantity=1,
            is_active=True,
            start_date=today,
            end_date=today + timedelta(days=5)
        )
        
        # Test price within date range
        price = PricingService.get_price_for_client(self.client, self.product)
        self.assertEqual(price, Decimal('135.00'))
        
        # Test price outside date range
        rule.end_date = today - timedelta(days=1)
        rule.save()
        price = PricingService.get_price_for_client(self.client, self.product)
        self.assertEqual(price, Decimal('150.00'))

    def test_price_with_tax(self):
        """Test price calculation with tax"""
        # Regular price without discount
        price_ht = PricingService.get_price_for_client(self.client, self.product)
        expected_ttc = price_ht * (1 + self.product.tax_rate / 100)
        self.assertEqual(expected_ttc, Decimal('180.00'))  # 150 + 20% TVA
        
        # Price with discount
        rule = PriceRule.objects.create(
            price_grid=self.price_grid,
            product=self.product,
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_quantity=1,
            is_active=True
        )
        
        price_ht = PricingService.get_price_for_client(self.client, self.product)
        expected_ttc = price_ht * (1 + self.product.tax_rate / 100)
        self.assertEqual(expected_ttc, Decimal('162.00'))  # (150 - 10%) + 20% TVA

    def test_inactive_price_grid(self):
        """Test that inactive price grids are ignored"""
        self.price_grid.is_active = False
        self.price_grid.save()
        
        PriceRule.objects.create(
            price_grid=self.price_grid,
            product=self.product,
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_quantity=1,
            is_active=True
        )
        
        # Should return regular price since grid is inactive
        price = PricingService.get_price_for_client(self.client, self.product)
        self.assertEqual(price, Decimal('150.00'))

    def test_inactive_price_rule(self):
        """Test that inactive price rules are ignored"""
        rule = PriceRule.objects.create(
            price_grid=self.price_grid,
            product=self.product,
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_quantity=1,
            is_active=False
        )
        
        # Should return regular price since rule is inactive
        price = PricingService.get_price_for_client(self.client, self.product)
        self.assertEqual(price, Decimal('150.00'))

    def test_multiple_active_rules(self):
        """Test that the most advantageous rule is applied"""
        # Create two rules for the same product
        PriceRule.objects.create(
            price_grid=self.price_grid,
            product=self.product,
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_quantity=1,
            is_active=True
        )
        
        PriceRule.objects.create(
            price_grid=self.price_grid,
            product=self.product,
            discount_type='percentage',
            discount_value=Decimal('15.00'),
            min_quantity=1,
            is_active=True
        )
        
        # Should apply the 15% discount as it's more advantageous
        price = PricingService.get_price_for_client(self.client, self.product)
        self.assertEqual(price, Decimal('127.50'))

    def test_client_without_segment(self):
        """Test pricing for client without segment"""
        client_without_segment = Client.objects.create(
            name="No Segment Client"
        )
        
        # Should return regular price
        price = PricingService.get_price_for_client(client_without_segment, self.product)
        self.assertEqual(price, Decimal('150.00')) 