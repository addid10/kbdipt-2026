from django.contrib.auth import get_user_model
from django.test import TestCase

from peatlandcovers.models import PeatlandSite


User = get_user_model()


class UserAuthenticationTests(TestCase):
    def test_login_page_is_available(self):
        response = self.client.get("/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Masuk ke akun Anda")
        self.assertNotContains(response, "Login Operator")


    def test_staff_account_is_not_logged_in_through_user_portal(self):
        staff = User.objects.create_user(
            username="operator",
            email="operator@example.com",
            password="KbdiOperator-2026!",
            is_staff=True,
        )
        response = self.client.post(
            "/login/",
            {"username": staff.username, "password": "KbdiOperator-2026!"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Akun ini tidak digunakan pada portal pengguna.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_registration_page_is_available(self):
        response = self.client.get("/register/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Buat Akun Pengguna")

    def test_registration_creates_and_logs_in_user(self):
        response = self.client.post(
            "/register/",
            {
                "full_name": "Test User",
                "email": "test.user@example.com",
                "username": "testuser",
                "password1": "KbdiTest-2026-Secure!",
                "password2": "KbdiTest-2026-Secure!",
            },
        )
        self.assertRedirects(response, "/")
        user = User.objects.get(username="testuser")
        self.assertEqual(user.email, "test.user@example.com")
        self.assertEqual(user.first_name, "Test User")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(
            username="existing",
            email="duplicate@example.com",
            password="KbdiExisting-2026!",
        )
        response = self.client.post(
            "/register/",
            {
                "full_name": "Another User",
                "email": "DUPLICATE@example.com",
                "username": "anotheruser",
                "password1": "KbdiTest-2026-Secure!",
                "password2": "KbdiTest-2026-Secure!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email ini sudah terdaftar.")
        self.assertFalse(User.objects.filter(username="anotheruser").exists())


class PublicInterfaceTests(TestCase):
    def setUp(self):
        self.site = PeatlandSite.objects.create(
            name="Hutan Lindung Liang Anggang Block 1",
            code="liang-anggang-block-1",
        )
        self.user = User.objects.create_user(
            username="monitoringuser",
            email="monitoring@example.com",
            password="KbdiMonitoring-2026!",
        )

    def test_public_home_requires_login(self):
        response = self.client.get("/")
        self.assertRedirects(response, "/login/?next=/")

    def test_public_site_detail_requires_login(self):
        response = self.client.get("/locations/liang-anggang-block-1/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/login/?next="))

    def test_authenticated_home_is_available(self):
        self.client.force_login(self.user)
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "KBDIpt")
        self.assertContains(response, "Profil")
        self.assertNotContains(response, "Login Operator")
        self.assertNotContains(response, "Akses Operator / Admin")

    def test_authenticated_site_detail_is_available(self):
        self.client.force_login(self.user)
        response = self.client.get("/locations/liang-anggang-block-1/")
        self.assertEqual(response.status_code, 200)

    def test_profile_is_available_to_authenticated_user(self):
        self.client.force_login(self.user)
        response = self.client.get("/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "@monitoringuser")
        self.assertContains(response, "Keluar dari Akun")

    def test_info_does_not_expose_operator_login(self):
        self.client.force_login(self.user)
        response = self.client.get("/info/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "management/login")
        self.assertNotContains(response, "Akses Operator")

    def test_regular_user_cannot_open_management_dashboard(self):
        self.client.force_login(self.user)
        response = self.client.get("/management/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/management/login/"))

    def test_user_logout_uses_post(self):
        self.client.force_login(self.user)
        response = self.client.get("/logout/")
        self.assertEqual(response.status_code, 405)
        response = self.client.post("/logout/")
        self.assertRedirects(response, "/login/")
        self.assertNotIn("_auth_user_id", self.client.session)
