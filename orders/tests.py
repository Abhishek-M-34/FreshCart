from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from cart.models import Cart, CartItem
from products.models import Category, Product, StockBatch

from .models import Order, OrderItem


class OrderTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="customer",
            password="TestPassword123"
        )

        self.admin = User.objects.create_user(
            username="admin",
            password="AdminPassword123",
            is_staff=True
        )

        self.other_user = User.objects.create_user(
            username="otheruser",
            password="OtherPassword123"
        )

        self.category = Category.objects.create(
            name="Fruits",
            description="Fresh fruits"
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Apple",
            description="Fresh apple",
            price=Decimal("100.00"),
            stock=20,
            is_available=True
        )

        self.second_product = Product.objects.create(
            category=self.category,
            name="Banana",
            description="Fresh banana",
            price=Decimal("50.00"),
            stock=10,
            is_available=True
        )
        StockBatch.objects.create(
            product=self.product,
            quantity_received=20,
            quantity_remaining=20,
            arrival_date=date.today(),
            expiry_date=date.today() + timedelta(days=5)
        )

        StockBatch.objects.create(
            product=self.second_product,
            quantity_received=10,
            quantity_remaining=10,
            arrival_date=date.today(),
            expiry_date=date.today() + timedelta(days=5)
        )

    def login_customer(self):
        self.client.login(
            username="customer",
            password="TestPassword123"
        )

    def login_admin(self):
        self.client.login(
            username="admin",
            password="AdminPassword123"
        )

    def create_cart_with_items(self):
        cart = Cart.objects.create(
            user=self.user
        )

        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=2
        )

        CartItem.objects.create(
            cart=cart,
            product=self.second_product,
            quantity=3
        )

        return cart

    def test_checkout_requires_login(self):
        response = self.client.get(
            reverse("checkout")
        )

        self.assertEqual(
            response.status_code,
            302
        )

        self.assertIn(
            "/login/",
            response.url
        )

    def test_checkout_requires_cart(self):
        self.login_customer()

        response = self.client.get(
            reverse("checkout")
        )

        self.assertEqual(
            response.status_code,
            404
        )

    def test_checkout_empty_cart_redirects_to_cart(self):
        self.login_customer()

        Cart.objects.create(
            user=self.user
        )

        response = self.client.get(
            reverse("checkout")
        )

        self.assertRedirects(
            response,
            reverse("cart")
        )

    def test_checkout_page_loads_with_cart_items(self):
        self.login_customer()

        self.create_cart_with_items()

        response = self.client.get(
            reverse("checkout")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertTemplateUsed(
            response,
            "orders/checkout.html"
        )

        self.assertContains(
            response,
            "Apple"
        )

        self.assertContains(
            response,
            "Banana"
        )

        self.assertEqual(
            response.context["total"],
            Decimal("350.00")
        )

    def test_successful_checkout_creates_order(self):
        cart = self.create_cart_with_items()

        self.login_customer()

        response = self.client.post(
            reverse("checkout"),
            {
                "shipping_address": (
                    "123 Main Street, "
                    "Trivandrum, Kerala"
                )
            }
        )

        order = Order.objects.get(
            user=self.user
        )

        self.assertRedirects(
            response,
            reverse(
                "order_success",
                args=[order.id]
            )
        )

        self.assertEqual(
            order.total_amount,
            Decimal("350.00")
        )

        self.assertEqual(
            order.shipping_address,
            "123 Main Street, Trivandrum, Kerala"
        )

        self.assertEqual(
            order.status,
            "pending"
        )

    def test_checkout_creates_order_items(self):
        self.create_cart_with_items()

        self.login_customer()

        self.client.post(
            reverse("checkout"),
            {
                "shipping_address": "Test Address"
            }
        )

        order = Order.objects.get(
            user=self.user
        )

        self.assertEqual(
            order.items.count(),
            2
        )

        apple_item = order.items.get(
            product=self.product
        )

        banana_item = order.items.get(
            product=self.second_product
        )

        self.assertEqual(
            apple_item.product_name,
            "Apple"
        )

        self.assertEqual(
            apple_item.price,
            Decimal("100.00")
        )

        self.assertEqual(
            apple_item.quantity,
            2
        )

        self.assertEqual(
            banana_item.product_name,
            "Banana"
        )

        self.assertEqual(
            banana_item.price,
            Decimal("50.00")
        )

        self.assertEqual(
            banana_item.quantity,
            3
        )

    def test_checkout_reduces_batch_stock(self):
        self.create_cart_with_items()

        self.login_customer()

        self.client.post(
            reverse("checkout"),
            {
                "shipping_address": "Test Address"
            }
        )

        self.product.refresh_from_db()
        self.second_product.refresh_from_db()

        self.assertEqual(
            self.product.get_available_stock(),
            18
        )

        self.assertEqual(
            self.second_product.get_available_stock(),
            7
        )

    def test_checkout_clears_cart(self):
        cart = self.create_cart_with_items()

        self.login_customer()

        self.client.post(
            reverse("checkout"),
            {
                "shipping_address": "Test Address"
            }
        )

        self.assertEqual(
            cart.items.count(),
            0
        )

    def test_stock_zero_makes_product_unavailable(self):
        product = Product.objects.create(
            category=self.category,
            name="Orange",
            description="Fresh orange",
            price=Decimal("80.00"),
            stock=2,
            is_available=True
        )

        cart = Cart.objects.create(
            user=self.user
        )

        CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=2
        )

        self.login_customer()

        StockBatch.objects.create(
            product=product,
            quantity_received=2,
            quantity_remaining=2,
            arrival_date=date.today(),
            expiry_date=date.today() + timedelta(days=5)
        )

        self.client.post(
            reverse("checkout"),
            {
                "shipping_address": "Test Address"
            }
        )

        product.refresh_from_db()

        self.assertEqual(
            product.get_available_stock(),
            0
        )

    def test_checkout_rejects_insufficient_stock(self):
        cart = Cart.objects.create(
            user=self.user
        )

        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=25
        )

        self.login_customer()

        response = self.client.post(
            reverse("checkout"),
            {
                "shipping_address": "Test Address"
            }
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertTemplateUsed(
            response,
            "orders/checkout.html"
        )

        self.assertContains(
            response,
            "Apple is no longer available"
        )

        self.assertEqual(
            Order.objects.filter(
                user=self.user
            ).count(),
            0
        )

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.get_available_stock(),
            20
        )

    def test_order_success_page(self):
        self.login_customer()

        order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("250.00"),
            shipping_address="Test Address",
            status="pending"
        )

        response = self.client.get(
            reverse(
                "order_success",
                args=[order.id]
            )
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertTemplateUsed(
            response,
            "orders/order_success.html"
        )

        self.assertEqual(
            response.context["order"],
            order
        )

    def test_order_success_cannot_access_other_users_order(self):
        self.login_customer()

        order = Order.objects.create(
            user=self.other_user,
            total_amount=Decimal("250.00"),
            shipping_address="Other Address",
            status="pending"
        )

        response = self.client.get(
            reverse(
                "order_success",
                args=[order.id]
            )
        )

        self.assertEqual(
            response.status_code,
            404
        )

    def test_order_history(self):
        self.login_customer()

        Order.objects.create(
            user=self.user,
            total_amount=Decimal("100.00"),
            shipping_address="Address 1",
            status="pending"
        )

        Order.objects.create(
            user=self.user,
            total_amount=Decimal("200.00"),
            shipping_address="Address 2",
            status="delivered"
        )

        response = self.client.get(
            reverse("order_history")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertTemplateUsed(
            response,
            "orders/order_history.html"
        )

        self.assertEqual(
            response.context["orders"].count(),
            2
        )

    def test_order_history_requires_login(self):
        response = self.client.get(
            reverse("order_history")
        )

        self.assertEqual(
            response.status_code,
            302
        )

        self.assertIn(
            "/login/",
            response.url
        )

    def test_order_detail(self):
        self.login_customer()

        order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("200.00"),
            shipping_address="Test Address",
            status="pending"
        )

        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name="Apple",
            price=Decimal("100.00"),
            quantity=2
        )

        response = self.client.get(
            reverse(
                "order_detail",
                args=[order.id]
            )
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertTemplateUsed(
            response,
            "orders/order_detail.html"
        )

        self.assertEqual(
            response.context["order"],
            order
        )

        self.assertEqual(
            response.context["items"].count(),
            1
        )

        item = response.context["items"][0]

        self.assertEqual(
            item.subtotal,
            Decimal("200.00")
        )

    def test_customer_cannot_view_other_users_order(self):
        self.login_customer()

        order = Order.objects.create(
            user=self.other_user,
            total_amount=Decimal("200.00"),
            shipping_address="Other Address",
            status="pending"
        )

        response = self.client.get(
            reverse(
                "order_detail",
                args=[order.id]
            )
        )

        self.assertEqual(
            response.status_code,
            404
        )

    def test_admin_can_view_order_list(self):
        Order.objects.create(
            user=self.user,
            total_amount=Decimal("200.00"),
            shipping_address="Test Address",
            status="pending"
        )

        self.login_admin()

        response = self.client.get(
            reverse("admin_order_list")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertTemplateUsed(
            response,
            "dashboard/orders/order_list.html"
        )

        self.assertEqual(
            response.context["orders"].count(),
            1
        )

    def test_non_admin_cannot_view_admin_order_list(self):
        self.login_customer()

        response = self.client.get(
            reverse("admin_order_list")
        )

        self.assertEqual(
            response.status_code,
            302
        )

        self.assertIn(
            "/login/",
            response.url
        )

    def test_admin_can_view_order_detail(self):
        self.login_admin()

        order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("200.00"),
            shipping_address="Test Address",
            status="pending"
        )

        response = self.client.get(
            reverse(
                "admin_order_detail",
                args=[order.id]
            )
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertTemplateUsed(
            response,
            "dashboard/orders/order_detail.html"
        )

        self.assertEqual(
            response.context["order"],
            order
        )

    def test_admin_can_update_order_status(self):
        self.login_admin()

        order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("200.00"),
            shipping_address="Test Address",
            status="pending"
        )

        response = self.client.post(
            reverse(
                "admin_order_update",
                args=[order.id]
            ),
            {
                "status": "shipped"
            }
        )

        self.assertRedirects(
            response,
            reverse(
                "admin_order_detail",
                args=[order.id]
            )
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            "shipped"
        )

    def test_non_admin_cannot_update_order_status(self):
        self.login_customer()

        order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("200.00"),
            shipping_address="Test Address",
            status="pending"
        )

        response = self.client.post(
            reverse(
                "admin_order_update",
                args=[order.id]
            ),
            {
                "status": "shipped"
            }
        )

        self.assertEqual(
            response.status_code,
            302
        )

        self.assertIn(
            "/login/",
            response.url
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            "pending"
        )

    def test_fefo_consumes_earlier_expiry_batch_first(self):
        """Checkout should consume the batch that expires first."""
        today = date.today()

        early_batch = StockBatch.objects.create(
            product=self.product,
            quantity_received=10,
            quantity_remaining=10,
            arrival_date=today,
            expiry_date=today + timedelta(days=2),
        )

        late_batch = StockBatch.objects.create(
            product=self.product,
            quantity_received=10,
            quantity_remaining=10,
            arrival_date=today,
            expiry_date=today + timedelta(days=5),
        )

        cart = Cart.objects.get(user=self.user)

        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=6,
        )

        response = self.client.post(
            reverse("checkout")
        )

        early_batch.refresh_from_db()
        late_batch.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(early_batch.quantity_remaining, 4)
        self.assertEqual(late_batch.quantity_remaining, 10)

    def test_fefo_consumes_across_multiple_batches(self):
        """Checkout should consume from the next batch when the first is insufficient."""
        today = date.today()

        first_batch = StockBatch.objects.create(
            product=self.product,
            quantity_received=5,
            quantity_remaining=5,
            arrival_date=today,
            expiry_date=today + timedelta(days=2),
        )

        second_batch = StockBatch.objects.create(
            product=self.product,
            quantity_received=10,
            quantity_remaining=10,
            arrival_date=today,
            expiry_date=today + timedelta(days=5),
        )   

        cart = Cart.objects.get(user=self.user)

        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=8,
        )

        response = self.client.post(
            reverse("checkout")
        )

        first_batch.refresh_from_db()
        second_batch.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(first_batch.quantity_remaining, 0)
        self.assertEqual(second_batch.quantity_remaining, 7)

    def test_fefo_skips_expired_batch(self):
        """Expired stock should never be consumed during checkout."""
        today = date.today()

        expired_batch = StockBatch.objects.create(
            product=self.product,
            quantity_received=10,
            quantity_remaining=10,
            arrival_date=today - timedelta(days=5),
            expiry_date=today - timedelta(days=1),
        )

        valid_batch = StockBatch.objects.create(
            product=self.product,
            quantity_received=10,
            quantity_remaining=10,
            arrival_date=today,
            expiry_date=today + timedelta(days=5),
        )

        cart = Cart.objects.get(user=self.user)

        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=5,
        )

        response = self.client.post(
            reverse("checkout")
        )

        expired_batch.refresh_from_db()
        valid_batch.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(expired_batch.quantity_remaining, 10)
        self.assertEqual(valid_batch.quantity_remaining, 5)

    def test_fefo_consumes_non_expiring_batch_last(self):
        """A non-expiring batch should be consumed after batches with expiry dates."""
        today = date.today()

        expiring_batch = StockBatch.objects.create(
            product=self.product,
            quantity_received=5,
            quantity_remaining=5,
            arrival_date=today,
            expiry_date=today + timedelta(days=5),
        )

        non_expiring_batch = StockBatch.objects.create(
            product=self.product,
            quantity_received=10,
            quantity_remaining=10,
            arrival_date=today,
            expiry_date=None,
        )

        cart = Cart.objects.get(user=self.user)

        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=8,
        )

        response = self.client.post(
            reverse("checkout")
        )

        expiring_batch.refresh_from_db()
        non_expiring_batch.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(expiring_batch.quantity_remaining, 0)
        self.assertEqual(non_expiring_batch.quantity_remaining, 7)