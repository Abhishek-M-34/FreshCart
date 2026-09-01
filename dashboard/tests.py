from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from orders.models import Order
from products.models import Category, Product


class DashboardTests(TestCase):

    def setUp(self):
        self.customer = User.objects.create_user(
            username="customer",
            password="TestPassword123"
        )

        self.admin = User.objects.create_user(
            username="admin",
            password="AdminPassword123",
            is_staff=True
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

    def login_admin(self):
        self.client.login(
            username="admin",
            password="AdminPassword123"
        )

    def login_customer(self):
        self.client.login(
            username="customer",
            password="TestPassword123"
        )

    def test_dashboard_requires_admin(self):
        response = self.client.get(
            reverse("admin_dashboard")
        )

        self.assertEqual(
            response.status_code,
            302
        )

        self.assertIn(
            "/login/",
            response.url
        )

    def test_dashboard_requires_staff(self):
        self.login_customer()

        response = self.client.get(
            reverse("admin_dashboard")
        )

        self.assertEqual(
            response.status_code,
            302
        )

        self.assertIn(
            "/login/",
            response.url
        )

    def test_admin_can_access_dashboard(self):
        self.login_admin()

        response = self.client.get(
            reverse("admin_dashboard")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertTemplateUsed(
            response,
            "dashboard/dashboard.html"
        )

    def test_dashboard_contains_statistics(self):
        Order.objects.create(
            user=self.customer,
            total_amount=Decimal("200.00"),
            shipping_address="Test Address",
            status="delivered"
        )

        self.login_admin()

        response = self.client.get(
            reverse("admin_dashboard")
        )

        self.assertEqual(
            response.context["total_products"],
            1
        )

        self.assertEqual(
            response.context["total_customers"],
            1
        )

        self.assertEqual(
            response.context["total_orders"],
            1
        )

        self.assertEqual(
            response.context["total_revenue"],
            Decimal("200.00")
        )

    def test_customer_list_requires_admin(self):
        self.login_customer()

        response = self.client.get(
            reverse("admin_customer_list")
        )

        self.assertEqual(
            response.status_code,
            302
        )

        self.assertIn(
            "/login/",
            response.url
        )

    def test_admin_can_access_customer_list(self):
        self.login_admin()

        response = self.client.get(
            reverse("admin_customer_list")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertTemplateUsed(
            response,
            "dashboard/customers/customer_list.html"
        )

    def test_customer_detail(self):
        self.login_admin()

        response = self.client.get(
            reverse(
                "admin_customer_detail",
                args=[self.customer.id]
            )
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertTemplateUsed(
            response,
            "dashboard/customers/customer_detail.html"
        )

        self.assertEqual(
            response.context["customer"],
            self.customer
        )

    def test_analytics_requires_admin(self):
        self.login_customer()

        response = self.client.get(
            reverse("analytics")
        )

        self.assertEqual(
            response.status_code,
            302
        )

        self.assertIn(
            "/login/",
            response.url
        )

    def test_admin_can_access_analytics(self):
        self.login_admin()

        response = self.client.get(
            reverse("analytics")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertTemplateUsed(
            response,
            "dashboard/analytics.html"
        )

    def test_analytics_contains_sales_data(self):
        order = Order.objects.create(
            user=self.customer,
            total_amount=Decimal("200.00"),
            shipping_address="Test Address",
            status="delivered"
        )

        from orders.models import OrderItem

        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name="Apple",
            price=Decimal("100.00"),
            quantity=2
        )

        self.login_admin()

        response = self.client.get(
            reverse("analytics")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.context["total_revenue"],
            Decimal("200.00")
        )

        self.assertEqual(
            response.context["total_orders"],
            1
        )

        self.assertEqual(
            response.context["average_order_value"],
            Decimal("200.00")
        )