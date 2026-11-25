from datetime import date, time, timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from config.urls import handler500
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils.module_loading import import_string

from accounts.models import ProfessionalApplication, User
from .models import Appointment, Feedback, Notification, ReflectionResponse


class CustomErrorPageTests(TestCase):
    @override_settings(DEBUG=False)
    def test_missing_page_uses_friendly_404_template(self):
        response = self.client.get("/page-that-does-not-exist/")

        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "core/404.html")
        self.assertContains(response, "We couldn't find that page.", status_code=404)

    @override_settings(DEBUG=False)
    def test_server_error_handler_uses_friendly_500_template(self):
        handler = import_string(handler500)
        response = handler(RequestFactory().get("/"))

        self.assertEqual(response.status_code, 500)
        self.assertIn(b"We couldn't complete your request.", response.content)


class MindBridgeWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="member",
            email="member@example.com",
            password="StrongPass!548",
        )
        self.professional = User.objects.create_user(
            username="professional",
            email="professional@example.com",
            password="StrongPass!548",
            role=User.Role.PROFESSIONAL,
        )
        self.application = ProfessionalApplication.objects.create(
            applicant=self.professional,
            full_name="Alice Example",
            professional_title="Counsellor",
            organisation="Example Clinic",
            qualifications="Sample qualification",
            licence_number="SAMPLE-123",
            years_experience=4,
            biography="Professional sample biography",
            contact_email="professional@example.com",
            consent_to_directory=True,
            status=ProfessionalApplication.Status.APPROVED,
        )

    def test_assessment_submission_creates_result(self):
        self.client.login(username="member", password="StrongPass!548")
        response = self.client.post(reverse("self_awareness"), {
            "mood": "2",
            "energy": "2",
            "stress": "2",
            "connection": "2",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Extra care may be helpful")
        self.assertContains(response, "This is not a diagnosis.")
        self.assertNotContains(response, "Reflection score:")
        reflection = ReflectionResponse.objects.get(user=self.user)
        self.assertEqual(reflection.score, 8)

    def test_assessment_rejects_incomplete_submission(self):
        self.client.login(username="member", password="StrongPass!548")
        response = self.client.post(reverse("self_awareness"), {"mood": "0"})
        self.assertContains(response, "Please answer all four questions")

    @patch("core.views.timezone.localdate", return_value=date(2025, 1, 1))
    def test_wellness_page_shows_the_date_selected_tip_only(self, _mock_date):
        response = self.client.get(reverse("wellness_tips"))

        self.assertContains(response, "Eat Regularly and Stay Hydrated")
        self.assertNotContains(response, "Prioritise Rest")
        self.assertNotContains(response, "Make Time for What You Enjoy")

    def test_directory_only_shows_approved_consented_applications(self):
        pending_user = User.objects.create_user(username="pending")
        ProfessionalApplication.objects.create(
            applicant=pending_user,
            full_name="Hidden Applicant",
            professional_title="Psychologist",
            qualifications="Sample",
            years_experience=2,
            biography="Hidden",
            contact_email="hidden@example.com",
            consent_to_directory=True,
            status=ProfessionalApplication.Status.PENDING,
        )
        no_consent_user = User.objects.create_user(username="no_consent")
        ProfessionalApplication.objects.create(
            applicant=no_consent_user,
            full_name="No Consent Applicant",
            professional_title="Counsellor",
            qualifications="Sample",
            years_experience=2,
            biography="Hidden",
            contact_email="no-consent@example.com",
            consent_to_directory=False,
            status=ProfessionalApplication.Status.APPROVED,
        )
        response = self.client.get(reverse("professional_directory"))
        self.assertContains(response, "Alice Example")
        self.assertNotContains(response, "Hidden Applicant")
        self.assertNotContains(response, "No Consent Applicant")

    def test_appointment_request_redirects_to_login_and_returns_to_professional(self):
        request_url = reverse("appointment_request", args=[self.application.pk])

        response = self.client.get(request_url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            parse_qs(urlsplit(response.url).query).get("next"),
            [request_url],
        )
        login_response = self.client.post(reverse("login"), {
            "username": "member",
            "password": "StrongPass!548",
            "next": request_url,
        })
        self.assertRedirects(login_response, request_url)
        self.assertEqual(self.client.get(request_url).status_code, 200)

    def test_directory_search_filters_results(self):
        self.client.login(username="member", password="StrongPass!548")
        response = self.client.get(
            reverse("professional_directory"),
            {"title": "Counsellor"},
        )
        self.assertContains(response, "Alice Example")
        response = self.client.get(
            reverse("professional_directory"),
            {"title": "Psychiatrist"},
        )
        self.assertNotContains(response, "Alice Example")

    def test_appointment_notifications_are_shown_before_being_marked_read(self):
        notification = Notification.objects.create(
            user=self.user,
            message="A private appointment update.",
        )
        self.client.login(username="member", password="StrongPass!548")

        response = self.client.get(reverse("appointment_list"))

        self.assertContains(response, "A private appointment update.")
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertNotContains(
            self.client.get(reverse("appointment_list")),
            "A private appointment update.",
        )

    def test_appointment_request_and_professional_access(self):
        self.client.login(username="member", password="StrongPass!548")
        response = self.client.post(
            reverse("appointment_request", args=[self.application.pk]),
            {
                "requested_date": (date.today() + timedelta(days=2)).isoformat(),
                "requested_time": "10:30",
                "relevant_information": "private health details should not be stored",
            },
        )
        appointment = Appointment.objects.get(requester=self.user)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(appointment.status, Appointment.Status.PENDING)
        self.assertEqual(appointment.relevant_information, "")
        detail_response = self.client.get(response.url)
        self.assertNotContains(detail_response, "private health details")

        self.client.login(username="professional", password="StrongPass!548")
        response = self.client.post(
            reverse("appointment_detail", args=[appointment.pk]),
            {"action": "accept"},
        )
        appointment.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(appointment.status, Appointment.Status.ACCEPTED)

    def test_professional_cannot_accept_an_accepted_appointment(self):
        appointment = Appointment.objects.create(
            requester=self.user,
            professional=self.application,
            requested_date=date.today() + timedelta(days=1),
            requested_time=time(9, 0),
            status=Appointment.Status.ACCEPTED,
        )
        self.client.login(username="professional", password="StrongPass!548")

        response = self.client.post(
            reverse("appointment_detail", args=[appointment.pk]),
            {"action": "accept"},
        )

        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.ACCEPTED)
        self.assertContains(response, "Only pending appointments can be accepted.")

    def test_professional_cannot_reject_an_accepted_appointment(self):
        appointment = Appointment.objects.create(
            requester=self.user,
            professional=self.application,
            requested_date=date.today() + timedelta(days=1),
            requested_time=time(9, 0),
            status=Appointment.Status.ACCEPTED,
        )
        self.client.login(username="professional", password="StrongPass!548")

        response = self.client.post(
            reverse("appointment_detail", args=[appointment.pk]),
            {"action": "reject"},
        )

        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.ACCEPTED)
        self.assertContains(response, "Only pending appointments can be rejected.")

    def test_professional_cannot_reschedule_a_cancelled_appointment(self):
        appointment = Appointment.objects.create(
            requester=self.user,
            professional=self.application,
            requested_date=date.today() + timedelta(days=1),
            requested_time=time(9, 0),
            status=Appointment.Status.CANCELLED,
        )
        self.client.login(username="professional", password="StrongPass!548")

        response = self.client.post(
            reverse("appointment_detail", args=[appointment.pk]),
            {
                "action": "reschedule",
                "proposed_date": (date.today() + timedelta(days=3)).isoformat(),
                "proposed_time": "14:00",
                "professional_note": "Please use this new time.",
            },
        )

        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.CANCELLED)
        self.assertIsNone(appointment.proposed_date)
        self.assertContains(
            response,
            "Only pending or accepted appointments can be rescheduled.",
        )

    def test_requester_cannot_confirm_without_a_reschedule_proposal(self):
        appointment = Appointment.objects.create(
            requester=self.user,
            professional=self.application,
            requested_date=date.today() + timedelta(days=1),
            requested_time=time(9, 0),
            status=Appointment.Status.PENDING,
        )
        self.client.login(username="member", password="StrongPass!548")

        response = self.client.post(
            reverse("appointment_detail", args=[appointment.pk]),
            {"action": "confirm_reschedule"},
        )

        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.PENDING)
        self.assertContains(response, "There is no proposed time to confirm.")

    def test_ordinary_user_cannot_view_another_users_appointment(self):
        other = User.objects.create_user(
            username="other",
            password="StrongPass!548",
        )
        appointment = Appointment.objects.create(
            requester=other,
            professional=self.application,
            requested_date=date.today() + timedelta(days=1),
            requested_time=time(9, 0),
        )
        self.client.login(username="member", password="StrongPass!548")
        response = self.client.get(
            reverse("appointment_detail", args=[appointment.pk])
        )
        self.assertRedirects(response, reverse("dashboard"))

    def test_legacy_appointment_free_text_is_not_displayed(self):
        appointment = Appointment.objects.create(
            requester=self.user,
            professional=self.application,
            requested_date=date.today() + timedelta(days=1),
            requested_time=time(9, 0),
            relevant_information="legacy private request details",
            professional_note="legacy private response details",
        )
        self.client.login(username="member", password="StrongPass!548")

        response = self.client.get(
            reverse("appointment_detail", args=[appointment.pk])
        )

        self.assertNotContains(response, "legacy private request details")
        self.assertNotContains(response, "legacy private response details")

    def test_unapproved_user_cannot_act_as_professional(self):
        unapproved = User.objects.create_user(
            username="unapproved",
            password="StrongPass!548",
            role=User.Role.PROFESSIONAL,
        )
        appointment = Appointment.objects.create(
            requester=self.user,
            professional=self.application,
            requested_date=date.today() + timedelta(days=1),
            requested_time=time(11, 0),
        )
        self.client.login(username="unapproved", password="StrongPass!548")
        response = self.client.post(
            reverse("appointment_detail", args=[appointment.pk]),
            {"action": "accept"},
        )
        appointment.refresh_from_db()
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(appointment.status, Appointment.Status.PENDING)

    def test_rejection_and_reschedule_workflow(self):
        appointment = Appointment.objects.create(
            requester=self.user,
            professional=self.application,
            requested_date=date.today() + timedelta(days=1),
            requested_time=time(9, 0),
        )
        self.client.login(username="professional", password="StrongPass!548")
        response = self.client.post(
            reverse("appointment_detail", args=[appointment.pk]),
            {
                "action": "reschedule",
                "proposed_date": (date.today() + timedelta(days=3)).isoformat(),
                "proposed_time": "14:00",
                "professional_note": "private health details should not be stored",
            },
        )
        appointment.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(appointment.professional_note, "")
        self.assertEqual(
            appointment.status,
            Appointment.Status.RESCHEDULE_PROPOSED,
        )

        self.client.login(username="member", password="StrongPass!548")
        response = self.client.post(
            reverse("appointment_detail", args=[appointment.pk]),
            {"action": "confirm_reschedule"},
        )
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.ACCEPTED)

    def test_feedback_is_private_and_saved(self):
        self.client.login(username="member", password="StrongPass!548")
        response = self.client.post(reverse("feedback"), {
            "category": "GENERAL",
            "message": "private health details should not be stored",
        })
        self.assertEqual(response.status_code, 302)
        feedback = Feedback.objects.get(user=self.user)
        self.assertFalse(feedback.reviewed)
        self.assertEqual(feedback.message, "")

    def test_logged_out_user_can_submit_private_feedback(self):
        response = self.client.post(reverse("feedback"), {
            "category": "GENERAL",
            "message": "private health details should not be stored",
        })

        self.assertEqual(response.status_code, 302)
        feedback = Feedback.objects.get(user__isnull=True)
        self.assertIsNone(feedback.user)
        self.assertEqual(feedback.message, "")

    def test_admin_cannot_access_appointment_records(self):
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="AdminPass!548",
        )
        self.client.force_login(admin)

        self.assertEqual(self.client.get("/admin/core/appointment/").status_code, 404)
        self.assertEqual(self.client.get("/admin/core/notification/").status_code, 404)
        self.assertNotContains(self.client.get(reverse("admin:index")), "Appointments")

    def test_feedback_admin_does_not_display_legacy_free_text(self):
        feedback = Feedback.objects.create(
            user=self.user,
            category=Feedback.Category.GENERAL,
            message="legacy private feedback details",
        )
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="AdminPass!548",
        )
        self.client.force_login(admin)

        response = self.client.get(
            reverse("admin:core_feedback_change", args=[feedback.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "legacy private feedback details")

    def test_urgent_support_and_quick_exit_are_available(self):
        self.client.login(username="member", password="StrongPass!548")
        response = self.client.get(reverse("urgent_support"))
        self.assertContains(response, "awaiting confirmation")
        self.assertContains(response, "Quick Exit")
