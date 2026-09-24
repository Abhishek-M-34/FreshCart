from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from cart.models import Cart, CartItem
from .models import Category, Product, StockBatch
from datetime import date, timedelta
from unittest.mock import patch


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
        self.assertContains(response, "data-add-stock-link")
        self.assertContains(response, "Potato")

        self.assertNotContains(response, "Mango")

    def test_product_list_marks_card_out_of_stock_at_cart_limit(self):
        self.client.login(
            username="customer",
            password="TestPassword123"
        )
        cart = Cart.objects.create(
            user=self.user
        )
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=20,
        )

        response = self.client.get(reverse("product_list"))

        self.assertContains(response, "Out of stock")
        product = next(
            product
            for product in response.context["products"]
            if product.id == self.product.id
        )
        self.assertEqual(product.remaining_stock, 0)

    def test_product_list_reenables_stock_after_cart_item_removed(self):
        self.client.login(
            username="customer",
            password="TestPassword123"
        )
        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=20,
        )

        self.client.post(
            reverse("remove_from_cart", args=[cart_item.id])
        )

        response = self.client.get(reverse("product_list"))
        product = next(
            product
            for product in response.context["products"]
            if product.id == self.product.id
        )

        self.assertEqual(product.remaining_stock, 20)
        self.assertContains(response, "In stock")

    def test_manage_products_uses_valid_batch_stock(self):
        StockBatch.objects.filter(product=self.product).delete()
        StockBatch.objects.create(
            product=self.product,
            quantity_received=10,
            quantity_remaining=10,
            arrival_date=date.today() - timedelta(days=5),
            expiry_date=date.today() - timedelta(days=1),
        )
        StockBatch.objects.create(
            product=self.product,
            quantity_received=10,
            quantity_remaining=10,
            arrival_date=date.today(),
            expiry_date=date.today() + timedelta(days=5),
        )
        StockBatch.objects.create(
            product=self.product,
            quantity_received=5,
            quantity_remaining=5,
            arrival_date=date.today(),
            expiry_date=date.today() + timedelta(days=6),
        )
        self.product.stock = 0
        self.product.save(update_fields=["stock"])

        self.client.login(
            username="admin",
            password="AdminPassword123"
        )
        response = self.client.get(reverse("admin_product_list"))

        self.assertContains(response, "15 in stock")
        products = [
            product
            for section in response.context["category_sections"]
            for product in section["products"]
        ]
        self.assertEqual(
            next(product for product in products if product.id == self.product.id).available_stock,
            15,
        )

    def test_customer_availability_uses_valid_batch_stock(self):
        self.product.stock = 0
        self.product.save(update_fields=["stock"])

        response = self.client.get(
            reverse("product_detail", args=[self.product.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "In stock")
        self.assertContains(response, 'max="20"')

    def test_product_without_discount_shows_only_original_price(self):
        response = self.client.get(reverse("product_detail", args=[self.product.id]))

        self.assertContains(response, "₹100.00")
        self.assertNotContains(response, "0% OFF")

    def test_product_with_discount_shows_original_price_and_discount(self):
        StockBatch.objects.filter(product=self.product).update(
            expiry_date=date.today() + timedelta(days=1)
        )

        response = self.client.get(reverse("product_detail", args=[self.product.id]))

        self.assertContains(response, "₹100.00")
        self.assertContains(response, "₹70.00")
        self.assertContains(response, "30% OFF")

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

    def test_admin_product_list_links_to_stock_management(self):
        self.client.login(
            username="admin",
            password="AdminPassword123"
        )

        response = self.client.get(reverse("admin_product_list"))

        self.assertContains(
            response,
            reverse("admin_stock_list")
        )

    def test_stock_management_shows_grouped_batch_table(self):
        batch = StockBatch.objects.create(
            product=self.product,
            quantity_received=15,
            quantity_remaining=10,
            arrival_date=date.today(),
            expiry_date=date.today() + timedelta(days=5),
        )
        self.client.login(
            username="admin",
            password="AdminPassword123"
        )

        response = self.client.get(reverse("admin_stock_list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "dashboard/products/stock_list.html"
        )
        self.assertContains(response, "Inventory by Batch")
        self.assertContains(response, "Apple")
        self.assertContains(response, "Batch 1")
        self.assertContains(response, "15")
        self.assertContains(response, "10")
        self.assertContains(response, "Available")
        self.assertContains(
            response,
            reverse("admin_stock_edit", args=[batch.id])
        )

    def test_account_links_to_stock_management(self):
        self.client.login(
            username="admin",
            password="AdminPassword123"
        )

        response = self.client.get(reverse("account"))

        self.assertContains(response, "Stock Management")
        self.assertContains(
            response,
            reverse("admin_stock_list")
        )

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
            20
        )

    def test_product_edit_hides_legacy_stock_input(self):
        self.client.login(
            username="admin",
            password="AdminPassword123"
        )

        response = self.client.get(
            reverse(
                "admin_product_edit",
                args=[self.product.id]
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Current Stock")
        self.assertContains(response, "Stock Management")
        self.assertNotContains(response, 'name="stock"')

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
    f"/admin-dashboard/products/stock/add/?product={self.product.id}",
    {
        "quantity_received": 20,
        "arrival_date": arrival_date.strftime("%Y-%m-%d"),
    },
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

    def test_add_stock_page_shows_selected_product(self):
        response = self.client.get(
            reverse("admin_stock_add") + f"?product={self.product.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "dashboard/products/stock_form.html"
        )
        self.assertContains(response, "Add Stock")
        self.assertContains(response, self.product.name)
        self.assertContains(response, "Cancel")

    @patch("products.views.get_product_demand_prediction")
    def test_add_stock_prediction_uses_product_expiry_horizon(
        self,
        mock_prediction,
    ):
        self.product.expiry_days = 5
        self.product.save(update_fields=["expiry_days"])
        mock_prediction.return_value = 18

        response = self.client.get(
            reverse("admin_stock_add") + f"?product={self.product.id}"
        )

        self.assertEqual(response.status_code, 200)
        mock_prediction.assert_called_once_with(self.product, 5)
        self.assertEqual(response.context["prediction_horizon"], 5)
        self.assertEqual(response.context["predicted_demand"], 18)
        self.assertContains(response, "next 5 days")
        self.assertContains(response, "18 units")

    @patch("products.views.get_product_demand_prediction")
    def test_add_stock_prediction_unavailable_is_not_faked(
        self,
        mock_prediction,
    ):
        mock_prediction.return_value = None

        response = self.client.get(
            reverse("admin_stock_add") + f"?product={self.product.id}"
        )

        self.assertContains(
            response,
            "Prediction unavailable - insufficient sales history.",
        )
        self.assertIsNone(response.context["predicted_demand"])

    def test_add_stock_rejects_zero_quantity(self):
        response = self.client.post(
            reverse("admin_stock_add") + f"?product={self.product.id}",
            {
                "quantity_received": 0,
                "arrival_date": date.today(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ensure this value is greater than or equal to 1")
        self.assertFalse(
            StockBatch.objects.filter(product=self.product).exists()
        )

    def test_add_stock_rejects_negative_quantity(self):
        response = self.client.post(
            reverse("admin_stock_add") + f"?product={self.product.id}",
            {
                "quantity_received": -1,
                "arrival_date": date.today(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ensure this value is greater than or equal to 1")
        self.assertFalse(
            StockBatch.objects.filter(product=self.product).exists()
        )

    def test_add_stock_accepts_quantity_one(self):
        response = self.client.post(
            reverse("admin_stock_add") + f"?product={self.product.id}",
            {
                "quantity_received": 1,
                "arrival_date": date.today(),
            },
        )

        self.assertRedirects(
            response,
            reverse("admin_product_list")
        )
        self.assertTrue(
            StockBatch.objects.filter(
                product=self.product,
                quantity_received=1,
                quantity_remaining=1,
            ).exists()
        )

    def test_edit_stock_page_shows_batch_context(self):
        batch = StockBatch.objects.create(
            product=self.product,
            quantity_received=20,
            quantity_remaining=12,
            arrival_date=date.today(),
            expiry_date=date.today() + timedelta(days=5),
        )

        response = self.client.get(
            reverse("admin_stock_edit", args=[batch.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "dashboard/products/stock_edit.html"
        )
        self.assertContains(response, "Edit Stock Batch")
        self.assertContains(response, self.product.name)
        self.assertContains(response, "Save Changes")
        self.assertContains(response, "Cancel")

    def test_batch_discount_for_expiry(self):
        today = date.today()

        test_cases = [
            (today + timedelta(days=5), 0),
            (today + timedelta(days=3), 10),
            (today + timedelta(days=2), 20),
            (today + timedelta(days=1), 30),
            (today, 30),
            (today - timedelta(days=1), 0),
        ]

        for expiry_date, expected_discount in test_cases:
            batch = StockBatch.objects.create(
            product=self.product,
            quantity_received=20,
            quantity_remaining=20,
            arrival_date=today,
            expiry_date=expiry_date,
        )

            self.assertEqual(
            batch.get_discount_percentage(),
            expected_discount,
        )

            batch.delete()


    def test_batch_discount_respects_expected_demand(self):
        batch = StockBatch.objects.create(
        product=self.product,
        quantity_received=20,
        quantity_remaining=10,
        arrival_date=date.today(),
        expiry_date=date.today() + timedelta(days=1),
    )

        self.assertEqual(
        batch.get_discount_percentage(expected_demand=10),
        0,
    )

        self.assertEqual(
        batch.get_discount_percentage(expected_demand=5),
        30,
    )


    def test_batch_discounted_price(self):
        batch = StockBatch.objects.create(
        product=self.product,
        quantity_received=20,
        quantity_remaining=20,
        arrival_date=date.today(),
        expiry_date=date.today() + timedelta(days=1),
    )

        self.assertEqual(
        batch.get_discounted_price(),
        Decimal("21.00"),
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
    new_arrival_date + timedelta(
        days=self.product.expiry_days
    ),
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