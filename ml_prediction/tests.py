from decimal import Decimal
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from orders.models import Order, OrderItem
from products.models import Category, Product


class MLPredictionTests(TestCase):

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
            stock=50,
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

    def test_sales_prediction_requires_admin(self):
        response = self.client.get(
            reverse("sales_prediction")
        )

        self.assertEqual(
            response.status_code,
            302
        )

        self.assertIn(
            "/login/",
            response.url
        )

    def test_customer_cannot_access_sales_prediction(self):
        self.login_customer()

        response = self.client.get(
            reverse("sales_prediction")
        )

        self.assertEqual(
            response.status_code,
            302
        )

        self.assertIn(
            "/login/",
            response.url
        )

    def test_admin_can_access_sales_prediction(self):
        self.login_admin()

        response = self.client.get(
            reverse("sales_prediction")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertTemplateUsed(
            response,
            "dashboard/sales_prediction.html"
        )

    def test_inventory_prediction_requires_admin(self):
        response = self.client.get(
            reverse("inventory_prediction")
        )

        self.assertEqual(
            response.status_code,
            302
        )

        self.assertIn(
            "/login/",
            response.url
        )

    def test_customer_cannot_access_inventory_prediction(self):
        self.login_customer()

        response = self.client.get(
            reverse("inventory_prediction")
        )

        self.assertEqual(
            response.status_code,
            302
        )

        self.assertIn(
            "/login/",
            response.url
        )

    def test_admin_can_access_inventory_prediction(self):
        self.login_admin()

        response = self.client.get(
            reverse("inventory_prediction")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertTemplateUsed(
            response,
            "dashboard/inventory_prediction.html"
        )

    def test_sales_prediction_handles_insufficient_data(self):
        self.login_admin()

        response = self.client.get(
            reverse("sales_prediction")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    def test_inventory_prediction_handles_insufficient_data(self):
        self.login_admin()

        response = self.client.get(
            reverse("inventory_prediction")
        )

        self.assertEqual(
            response.status_code,
            200
        )