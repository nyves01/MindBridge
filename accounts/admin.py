
from django.contrib import admin
from django.db import transaction
from django.utils import timezone

from .models import User, ProfessionalApplication


@admin.register(User)
class UserAdmin(admin.ModelAdmin):

    list_display = (
        "username",
        "email",
        "role",
        "is_staff",
        "is_active",
    )

    list_filter = (
        "role",
        "is_staff",
        "is_active",
    )

    search_fields = (
        "username",
        "email",
    )


@admin.register(ProfessionalApplication)
class ProfessionalApplicationAdmin(admin.ModelAdmin):

    list_display = (
        "full_name",
        "professional_title",
        "applicant",
        "status",
        "consent_to_directory",
        "submitted_at",
    )

    list_filter = (
        "status",
        "consent_to_directory",
    )

    search_fields = (
        "full_name",
        "professional_title",
        "contact_email",
    )

    readonly_fields = (
        "applicant",
        "submitted_at",
        "reviewed_at",
        "reviewed_by",
    )

    fields = (
        "applicant",
        "full_name",
        "professional_title",
        "organisation",
        "qualifications",
        "licence_number",
        "years_experience",
        "biography",
        "contact_email",
        "consent_to_directory",
        "status",
        "administrator_notes",
        "submitted_at",
        "reviewed_at",
        "reviewed_by",
    )

    @transaction.atomic
    def save_model(self, request, obj, form, change):

        previous_status = None

        if change:
            previous_status = (
                ProfessionalApplication.objects
                .select_for_update()
                .get(pk=obj.pk)
                .status
            )

        status_changed = (
            not change or previous_status != obj.status
        )

        if status_changed:
            obj.reviewed_at = timezone.now()
            obj.reviewed_by = request.user

        super().save_model(request, obj, form, change)

        if obj.status == ProfessionalApplication.Status.APPROVED:
            obj.applicant.role = User.Role.PROFESSIONAL

        else:
            obj.applicant.role = User.Role.USER

        obj.applicant.save(update_fields=["role"])
