from django.conf import settings
from django.db import models


class ReflectionResponse(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reflection_responses",
    )
    answers = models.JSONField(default=dict)
    score = models.PositiveSmallIntegerField()
    guidance = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} reflection - {self.created_at:%Y-%m-%d}"


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"
        RESCHEDULE_PROPOSED = "RESCHEDULE_PROPOSED", "Reschedule proposed"
        CANCELLED = "CANCELLED", "Cancelled"
        COMPLETED = "COMPLETED", "Completed"

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="appointment_requests",
    )
    professional = models.ForeignKey(
        "accounts.ProfessionalApplication",
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    requested_date = models.DateField()
    requested_time = models.TimeField()
    relevant_information = models.TextField(
        blank=True,
        help_text="Share only information needed for the appointment.",
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
    )
    proposed_date = models.DateField(null=True, blank=True)
    proposed_time = models.TimeField(null=True, blank=True)
    professional_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["professional", "requested_date", "requested_time"]),
        ]

    def __str__(self):
        return f"{self.requester.username} with {self.professional.full_name}"


class Feedback(models.Model):
    class Category(models.TextChoices):
        GENERAL = "GENERAL", "General feedback"
        ACCESSIBILITY = "ACCESSIBILITY", "Accessibility"
        PROFESSIONAL = "PROFESSIONAL", "Professional support"
        BUG = "BUG", "Bug or technical issue"
        OTHER = "OTHER", "Other"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feedback",
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.GENERAL,
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed = models.BooleanField(default=False)
    administrator_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_category_display()} - {self.created_at:%Y-%m-%d}"


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    message = models.CharField(max_length=300)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
