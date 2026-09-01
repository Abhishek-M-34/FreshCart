from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse


class AccountTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPassword123"
        )

    def test_register_user(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password1": "NewPassword123",
                "password2": "NewPassword123",
            }
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("home"))

        self.assertTrue(
            User.objects.filter(username="newuser").exists()
        )

        self.assertEqual(
            int(self.client.session["_auth_user_id"]),
            User.objects.get(username="newuser").id
        )

    def test_login_success(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "testuser",
                "password": "TestPassword123",
            }
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("home"))

        self.assertEqual(
            int(self.client.session["_auth_user_id"]),
            self.user.id
        )

    def test_login_invalid_credentials(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "testuser",
                "password": "WrongPassword",
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Invalid username or password."
        )

        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout(self):
        self.client.login(
            username="testuser",
            password="TestPassword123"
        )

        response = self.client.get(reverse("logout"))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("login"))

        self.assertNotIn("_auth_user_id", self.client.session)

    def test_account_requires_login(self):
        response = self.client.get(reverse("account"))

        self.assertEqual(response.status_code, 302)

        expected_url = (
            reverse("login") + "?next=" + reverse("account")
        )

        self.assertRedirects(response, expected_url)

    def test_authenticated_user_can_access_account(self):
        self.client.login(
            username="testuser",
            password="TestPassword123"
        )

        response = self.client.get(reverse("account"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/account.html"
        )