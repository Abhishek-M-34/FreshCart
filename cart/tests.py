from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from products.models import Category, Product
from .models import Cart, CartItem


class CartTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="customer",
            password="TestPassword123"
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

        self.unavailable_product = Product.objects.create(
            category=self.category,
            name="Mango",
            description="Fresh mango",
            price=Decimal("150.00"),
            stock=0,
            is_available=False
        )

    def login_user(self):
        self.client.login(
            username="customer",
            password="TestPassword123"
        )

    def test_cart_requires_login(self):
        response = self.client.get(
            reverse("cart")
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_authenticated_user_can_view_cart(self):
        self.login_user()

        response = self.client.get(
            reverse("cart")
        )

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "cart/cart.html"
        )

    def test_cart_is_created_when_viewed(self):
        self.login_user()

        self.assertFalse(
            Cart.objects.filter(
                user=self.user
            ).exists()
        )

        self.client.get(
            reverse("cart")
        )

        self.assertTrue(
            Cart.objects.filter(
                user=self.user
            ).exists()
        )

    def test_add_product_to_cart(self):
        self.login_user()

        response = self.client.post(
            reverse(
                "add_to_cart",
                args=[self.product.id]
            )
        )

        self.assertRedirects(
            response,
            reverse("cart")
        )

        cart = Cart.objects.get(
            user=self.user
        )

        cart_item = CartItem.objects.get(
            cart=cart,
            product=self.product
        )

        self.assertEqual(
            cart_item.quantity,
            1
        )

    def test_add_same_product_increases_quantity(self):
        self.login_user()

        self.client.post(
            reverse(
                "add_to_cart",
                args=[self.product.id]
            )
        )

        self.client.post(
            reverse(
                "add_to_cart",
                args=[self.product.id]
            )
        )

        cart = Cart.objects.get(
            user=self.user
        )

        cart_item = CartItem.objects.get(
            cart=cart,
            product=self.product
        )

        self.assertEqual(
            cart_item.quantity,
            2
        )

    def test_add_product_does_not_exceed_stock(self):
        self.login_user()

        for _ in range(25):
            self.client.post(
                reverse(
                    "add_to_cart",
                    args=[self.product.id]
                )
            )

        cart = Cart.objects.get(
            user=self.user
        )

        cart_item = CartItem.objects.get(
            cart=cart,
            product=self.product
        )

        self.assertEqual(
            cart_item.quantity,
            self.product.stock
        )

    def test_unavailable_product_returns_404(self):
        self.login_user()

        response = self.client.post(
            reverse(
                "add_to_cart",
                args=[self.unavailable_product.id]
            )
        )

        self.assertEqual(
            response.status_code,
            404
        )

        self.assertFalse(
            Cart.objects.filter(
                user=self.user
            ).exists()
        )

    def test_update_cart_quantity(self):
        self.login_user()

        cart = Cart.objects.create(
            user=self.user
        )

        cart_item = CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=1
        )

        response = self.client.post(
            reverse(
                "update_cart",
                args=[cart_item.id]
            ),
            {
                "quantity": 5
            }
        )

        self.assertRedirects(
            response,
            reverse("cart")
        )

        cart_item.refresh_from_db()

        self.assertEqual(
            cart_item.quantity,
            5
        )

    def test_update_cart_quantity_above_stock_is_ignored(self):
        self.login_user()

        cart = Cart.objects.create(
            user=self.user
        )

        cart_item = CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=5
        )

        response = self.client.post(
            reverse(
                "update_cart",
                args=[cart_item.id]
            ),
            {
                "quantity": 25
            }
        )

        self.assertRedirects(
            response,
            reverse("cart")
        )

        cart_item.refresh_from_db()

        self.assertEqual(
            cart_item.quantity,
            5
        )

    def test_update_cart_quantity_zero_removes_item(self):
        self.login_user()

        cart = Cart.objects.create(
            user=self.user
        )

        cart_item = CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=2
        )

        response = self.client.post(
            reverse(
                "update_cart",
                args=[cart_item.id]
            ),
            {
                "quantity": 0
            }
        )

        self.assertRedirects(
            response,
            reverse("cart")
        )

        self.assertFalse(
            CartItem.objects.filter(
                id=cart_item.id
            ).exists()
        )

    def test_remove_cart_item(self):
        self.login_user()

        cart = Cart.objects.create(
            user=self.user
        )

        cart_item = CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=2
        )

        response = self.client.post(
            reverse(
                "remove_from_cart",
                args=[cart_item.id]
            )
        )

        self.assertRedirects(
            response,
            reverse("cart")
        )

        self.assertFalse(
            CartItem.objects.filter(
                id=cart_item.id
            ).exists()
        )

    def test_cart_total_is_calculated_in_view(self):
        self.login_user()

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

        response = self.client.get(
            reverse("cart")
        )

        expected_total = Decimal("350.00")

        self.assertEqual(
            response.context["total"],
            expected_total
        )

    def test_cart_item_subtotal_is_calculated(self):
        self.login_user()

        cart = Cart.objects.create(
            user=self.user
        )

        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=3
        )

        response = self.client.get(
            reverse("cart")
        )

        item = response.context["items"][0]

        expected_subtotal = Decimal("300.00")

        self.assertEqual(
            item.subtotal,
            expected_subtotal
        )