from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import ProfessionalApplication


DEMO_PASSWORD = "MindBridge-Demo-2026!"


class Command(BaseCommand):
    help = "Create or refresh the MindBridge demo user, professional, and admin."

    def handle(self, *args, **options):
        user_model = get_user_model()
        demo_user, user_created = self._get_demo_user(
            user_model,
            username="demo_user",
            email="demo.user@example.com",
            role=user_model.Role.USER,
        )
        professional, professional_created = self._get_demo_user(
            user_model,
            username="demo_professional",
            email="demo.professional@example.com",
            role=user_model.Role.PROFESSIONAL,
        )
        administrator, admin_created = self._get_demo_user(
            user_model,
            username="demo_admin",
            email="demo.admin@example.com",
            role=user_model.Role.USER,
            is_staff=True,
            is_superuser=True,
        )

        application, application_created = ProfessionalApplication.objects.get_or_create(
            applicant=professional,
            defaults={
                "full_name": "Demo Professional",
                "professional_title": "Counsellor",
                "organisation": "MindBridge Demo Clinic",
                "qualifications": "Demo profile for testing only.",
                "licence_number": "DEMO-0001",
                "years_experience": 5,
                "biography": "A demo professional profile for local testing.",
                "contact_email": professional.email,
                "consent_to_directory": True,
                "status": ProfessionalApplication.Status.APPROVED,
                "reviewed_at": timezone.now(),
                "reviewed_by": administrator,
            },
        )
        if not application_created:
            application.status = ProfessionalApplication.Status.APPROVED
            application.consent_to_directory = True
            application.save(update_fields=["status", "consent_to_directory"])

        created_count = sum(
            (user_created, professional_created, admin_created)
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo accounts ready ({created_count} account(s) created). "
                "Existing account passwords were not changed."
            )
        )

    @staticmethod
    def _get_demo_user(
        user_model,
        *,
        username,
        email,
        role,
        is_staff=False,
        is_superuser=False,
    ):
        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "role": role,
                "is_staff": is_staff,
                "is_superuser": is_superuser,
                "is_active": True,
            },
        )
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save(update_fields=["password"])
        else:
            user.email = email
            user.role = role
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.is_active = True
            user.save(update_fields=[
                "email",
                "role",
                "is_staff",
                "is_superuser",
                "is_active",
            ])
        return user, created
