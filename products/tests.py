from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Category, Product


class ProductTests(TestCase):

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

        self.category = Category.objects.create(
            name="Fruits",
            description="Fresh fruits"
        )

        self.other_category = Category.objects.create(
            name="Vegetables",
            description="Fresh vegetables"
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Apple",
            description="Fresh apple",
            price=Decimal("100.00"),
            stock=20,
            is_available=True
        )

        self.unavailable_product = Product.objects.create(
            category=self.category,
            name="Mango",
            description="Fresh mango",
            price=Decimal("150.00"),
            stock=10,
            is_available=False
        )

        self.other_product = Product.objects.create(
            category=self.other_category,
            name="Potato",
            description="Fresh potato",
            price=Decimal("50.00"),
            stock=30,
            is_available=True
        )

    def test_product_list(self):
        response = self.client.get(
            reverse("product_list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "products/product_list.html"
        )

        self.assertContains(response, "Apple")
        self.assertContains(response, "Potato")

        self.assertNotContains(response, "Mango")

    def test_product_list_category_filter(self):
        response = self.client.get(
            reverse("product_list"),
            {"category": self.category.id}
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "Apple")
        self.assertNotContains(response, "Potato")

    def test_product_detail(self):
        response = self.client.get(
            reverse(
                "product_detail",
                args=[self.product.id]
            )
        )

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "products/product_detail.html"
        )

        self.assertContains(response, "Apple")

    def test_unavailable_product_detail_returns_404(self):
        response = self.client.get(
            reverse(
                "product_detail",
                args=[self.unavailable_product.id]
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_admin_product_list_requires_staff(self):
        response = self.client.get(
            reverse("admin_product_list")
        )

        self.assertRedirects(
            response,
            "/login/?next=/admin-dashboard/products/"
        )

    def test_admin_product_list_for_staff(self):
        self.client.login(
            username="admin",
            password="AdminPassword123"
        )

        response = self.client.get(
            reverse("admin_product_list")
        )

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "dashboard/products/product_list.html"
        )

        self.assertContains(response, "Apple")

    def test_admin_can_add_product(self):
        self.client.login(
            username="admin",
            password="AdminPassword123"
        )

        response = self.client.post(
            reverse("admin_product_add"),
            {
                "name": "Banana",
                "category": self.category.id,
                "description": "Fresh banana",
                "price": "60.00",
                "stock": 25,
                "is_available": "on",
            }
        )

        self.assertRedirects(
            response,
            reverse("admin_product_list")
        )

        self.assertTrue(
            Product.objects.filter(
                name="Banana"
            ).exists()
        )

    def test_admin_can_edit_product(self):
        self.client.login(
            username="admin",
            password="AdminPassword123"
        )

        response = self.client.post(
            reverse(
                "admin_product_edit",
                args=[self.product.id]
            ),
            {
                "name": "Green Apple",
                "category": self.category.id,
                "description": "Updated apple",
                "price": "120.00",
                "stock": 15,
                "is_available": "on",
            }
        )

        self.assertRedirects(
            response,
            reverse("admin_product_list")
        )

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.name,
            "Green Apple"
        )

        self.assertEqual(
            self.product.price,
            Decimal("120.00")
        )

        self.assertEqual(
            self.product.stock,
            15
        )

    def test_admin_can_delete_product(self):
        self.client.login(
            username="admin",
            password="AdminPassword123"
        )

        response = self.client.post(
            reverse(
                "admin_product_delete",
                args=[self.product.id]
            )
        )

        self.assertRedirects(
            response,
            reverse("admin_product_list")
        )

        self.assertFalse(
            Product.objects.filter(
                id=self.product.id
            ).exists()
        )

    def test_admin_can_add_category(self):
        self.client.login(
            username="admin",
            password="AdminPassword123"
        )

        response = self.client.post(
            reverse("admin_category_add"),
            {
                "name": "Dairy"
            }
        )

        self.assertRedirects(
            response,
            reverse("admin_category_list")
        )

        self.assertTrue(
            Category.objects.filter(
                name="Dairy"
            ).exists()
        )

    def test_admin_can_edit_category(self):
        self.client.login(
            username="admin",
            password="AdminPassword123"
        )

        response = self.client.post(
            reverse(
                "admin_category_edit",
                args=[self.category.id]
            ),
            {
                "name": "Fresh Fruits"
            }
        )

        self.assertRedirects(
            response,
            reverse("admin_category_list")
        )

        self.category.refresh_from_db()

        self.assertEqual(
            self.category.name,
            "Fresh Fruits"
        )

    def test_admin_can_delete_category(self):
        self.client.login(
            username="admin",
            password="AdminPassword123"
        )

        response = self.client.post(
            reverse(
                "admin_category_delete",
                args=[self.category.id]
            )
        )

        self.assertRedirects(
            response,
            reverse("admin_category_list")
        )

        self.assertFalse(
            Category.objects.filter(
                id=self.category.id
            ).exists()
        )