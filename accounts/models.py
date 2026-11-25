
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    class Role(models.TextChoices):
        USER = "USER", "Platform User"
        PROFESSIONAL = "PROFESSIONAL", "Mental Health Professional"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
    )

    def __str__(self):
        return self.username

class ProfessionalApplication(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    applicant = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="professional_application"
    )

    full_name = models.CharField(max_length=150)

    professional_title = models.CharField(max_length=150)

    organisation = models.CharField(
        max_length=200,
        blank=True
    )

    qualifications = models.TextField()

    licence_number = models.CharField(
        max_length=100,
        blank=True
    )

    years_experience = models.PositiveIntegerField()

    biography = models.TextField()

    contact_email = models.EmailField()

    consent_to_directory = models.BooleanField(default=False)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    administrator_notes = models.TextField(blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_professional_applications"
    )

    def __str__(self):
        return f"{self.full_name} - {self.get_status_display()}"