from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .admin import ProfessionalApplicationAdmin
from .management.commands.seed_demo import DEMO_PASSWORD
from .models import ProfessionalApplication, User
from django.contrib.admin.sites import AdminSite


class AccountsWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="member",
            email="member@example.com",
            password="StrongPass!548",
        )

    def test_registration_and_login(self):
        response = self.client.post(reverse("register"), {
            "username": "newmember",
            "email": "newmember@example.com",
            "password1": "StrongPass!548",
            "password2": "StrongPass!548",
            "privacy_consent": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="newmember").exists())

    def test_registration_requires_privacy_consent(self):
        response = self.client.post(reverse("register"), {
            "username": "no_consent",
            "email": "no.consent@example.com",
            "password1": "StrongPass!548",
            "password2": "StrongPass!548",
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn("privacy_consent", response.context["form"].errors)
        self.assertFalse(User.objects.filter(username="no_consent").exists())
        self.assertContains(response, "I have read and accept the privacy notice")

    def test_registration_rejects_duplicate_email_case_insensitively(self):
        response = self.client.post(reverse("register"), {
            "username": "anothermember",
            "email": "MEMBER@example.com",
            "password1": "StrongPass!548",
            "password2": "StrongPass!548",
            "privacy_consent": "on",
        })

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "email",
            "An account with this email address already exists.",
        )
        self.assertFalse(User.objects.filter(username="anothermember").exists())

    def test_login_redirects_to_same_site_next_url(self):
        response = self.client.post(reverse("login"), {
            "username": "member",
            "password": "StrongPass!548",
            "next": reverse("account_settings"),
        })

        self.assertRedirects(response, reverse("account_settings"))

    def test_login_rejects_external_next_url(self):
        response = self.client.post(reverse("login"), {
            "username": "member",
            "password": "StrongPass!548",
            "next": "https://example.com/",
        })

        self.assertRedirects(response, reverse("dashboard"))

    def test_logout_redirects_to_login_and_clears_session(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("logout"), follow=True)

        self.assertRedirects(response, reverse("login"))
        self.assertContains(response, "You have been logged out.")
        self.assertRedirects(
            self.client.get(reverse("dashboard")),
            f"{reverse('login')}?next={reverse('dashboard')}",
        )

    def test_authenticated_session_cookie_refreshes_for_15_minutes(self):
        self.client.force_login(self.user)

        for _ in range(2):
            response = self.client.get(reverse("dashboard"))
            self.assertIn(settings.SESSION_COOKIE_NAME, response.cookies)
            self.assertEqual(
                int(response.cookies[settings.SESSION_COOKIE_NAME]["max-age"]),
                900,
            )

    def test_public_information_pages_open_without_login(self):
        for page in (
            "home",
            "education",
            "wellness_tips",
            "support_guide",
            "urgent_support",
            "feedback",
        ):
            with self.subTest(page=page):
                self.assertEqual(self.client.get(reverse(page)).status_code, 200)

    def test_password_change(self):
        self.client.login(username="member", password="StrongPass!548")
        response = self.client.post(reverse("password_change"), {
            "old_password": "StrongPass!548",
            "new_password1": "AnotherStrong!548",
            "new_password2": "AnotherStrong!548",
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("AnotherStrong!548"))

    def test_professional_application_submission(self):
        self.client.login(username="member", password="StrongPass!548")
        response = self.client.post(reverse("professional_application"), {
            "full_name": "Alice Example",
            "professional_title": "Counsellor",
            "organisation": "Example Clinic",
            "qualifications": "Verified sample qualification",
            "licence_number": "SAMPLE-123",
            "years_experience": 5,
            "biography": "Professional biography",
            "contact_email": "alice@example.com",
            "consent_to_directory": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ProfessionalApplication.objects.filter(applicant=self.user).exists()
        )

    def test_admin_approval_assigns_professional_role(self):
        application = ProfessionalApplication.objects.create(
            applicant=self.user,
            full_name="Alice Example",
            professional_title="Psychologist",
            organisation="Example Clinic",
            qualifications="Sample qualification",
            licence_number="",
            years_experience=3,
            biography="Biography",
            contact_email="alice@example.com",
            consent_to_directory=True,
            status=ProfessionalApplication.Status.PENDING,
        )
        administrator = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="AdminStrong!548",
        )
        application.status = ProfessionalApplication.Status.APPROVED
        model_admin = ProfessionalApplicationAdmin(
            ProfessionalApplication,
            AdminSite(),
        )
        model_admin.save_model(
            type("Request", (), {"user": administrator})(),
            application,
            None,
            True,
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.PROFESSIONAL)

    def test_account_deactivation_logs_out_user(self):
        self.client.login(username="member", password="StrongPass!548")
        response = self.client.post(reverse("deactivate_account"))
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)


class SeedDemoCommandTests(TestCase):
    def test_seed_demo_is_repeatable_and_creates_expected_roles(self):
        output = StringIO()
        call_command("seed_demo", stdout=output)
        demo_user = User.objects.get(username="demo_user")
        demo_user.set_password("ChangedDemo!2026")
        demo_user.save(update_fields=["password"])

        call_command("seed_demo", stdout=output)

        self.assertEqual(User.objects.filter(username__startswith="demo_").count(), 3)
        demo_user.refresh_from_db()
        professional = User.objects.get(username="demo_professional")
        administrator = User.objects.get(username="demo_admin")

        self.assertEqual(demo_user.role, User.Role.USER)
        self.assertTrue(demo_user.check_password("ChangedDemo!2026"))
        self.assertEqual(professional.role, User.Role.PROFESSIONAL)
        self.assertTrue(professional.check_password(DEMO_PASSWORD))
        self.assertTrue(
            ProfessionalApplication.objects.filter(
                applicant=professional,
                status=ProfessionalApplication.Status.APPROVED,
                consent_to_directory=True,
            ).exists()
        )
        self.assertTrue(administrator.is_staff)
        self.assertTrue(administrator.is_superuser)
        self.assertTrue(administrator.check_password(DEMO_PASSWORD))
