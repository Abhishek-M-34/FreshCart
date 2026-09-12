from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Category, Product, StockBatch
from datetime import date, timedelta


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
        StockBatch.objects.create(
    product=self.product,
    quantity_received=20,
    quantity_remaining=20,
    arrival_date=date.today(),
    expiry_date=date.today() + timedelta(days=5)
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
        StockBatch.objects.create(
    product=self.other_product,
    quantity_received=30,
    quantity_remaining=30,
    arrival_date=date.today(),
    expiry_date=date.today() + timedelta(days=5)
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
                "expiry_days": 5,
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
                "expiry_days": 5,
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



class StockBatchTests(TestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="stock_admin",
            password="AdminPassword123",
            is_staff=True
        )

        self.category = Category.objects.create(
            name="Dairy",
            description="Fresh dairy products"
        )

        self.product = Product.objects.create(
            category=self.category,
            name="FreshCart Milk",
            description="500 ml milk",
            price=Decimal("30.00"),
            stock=0,
            expiry_days=5,
            is_available=True
        )
        

        self.client.login(
            username="stock_admin",
            password="AdminPassword123"
        )

    def test_admin_can_add_stock_batch(self):

        arrival_date = date.today()

        response = self.client.post(
            reverse("admin_stock_add"),
            {
                "product": self.product.id,
                "quantity_received": 20,
                "arrival_date": arrival_date,
            }
        )

        self.assertRedirects(
            response,
            reverse("admin_product_list")
        )

        batch = StockBatch.objects.get(
            product=self.product
        )

        self.assertEqual(
            batch.quantity_received,
            20
        )

        self.assertEqual(
            batch.quantity_remaining,
            20
        )

        self.assertEqual(
            batch.expiry_date,
            arrival_date + timedelta(days=5)
        )

    def test_admin_can_edit_stock_batch(self):

        batch = StockBatch.objects.create(
            product=self.product,
            quantity_received=20,
            quantity_remaining=20,
            arrival_date=date.today(),
            expiry_date=date.today() + timedelta(days=5)
        )

        new_arrival_date = date.today() - timedelta(days=1)
        new_expiry_date = date.today() + timedelta(days=10)

        response = self.client.post(
            reverse(
                "admin_stock_edit",
                args=[batch.id]
            ),
            {
                "quantity_remaining": 12,
                "arrival_date": new_arrival_date,
                "expiry_date": new_expiry_date,
            }
        )

        self.assertRedirects(
            response,
            reverse("admin_stock_list")
        )

        batch.refresh_from_db()

        self.assertEqual(
            batch.quantity_received,
            20
        )

        self.assertEqual(
            batch.quantity_remaining,
            12
        )

        self.assertEqual(
            batch.arrival_date,
            new_arrival_date
        )

        self.assertEqual(
            batch.expiry_date,
            new_expiry_date
        )

    def test_admin_can_discard_stock_batch(self):

        batch = StockBatch.objects.create(
            product=self.product,
            quantity_received=20,
            quantity_remaining=15,
            arrival_date=date.today(),
            expiry_date=date.today() + timedelta(days=5)
        )

        response = self.client.post(
            reverse(
                "admin_stock_discard",
                args=[batch.id]
            )
        )

        self.assertRedirects(
            response,
            reverse("admin_stock_list")
        )

        batch.refresh_from_db()

        self.assertEqual(
            batch.quantity_received,
            20
        )

        self.assertEqual(
            batch.quantity_remaining,
            0
        )

        self.assertTrue(
            StockBatch.objects.filter(
                id=batch.id
            ).exists()
        )