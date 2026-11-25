
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import ProfessionalApplication
from .forms import (
    AppointmentRequestForm,
    FeedbackForm,
    RescheduleForm,
    SelfAwarenessForm,
)
from .models import Appointment, Notification, ReflectionResponse


WELLNESS_TIPS = (
    {
        "title": "Prioritise Rest",
        "description": (
            "Try to maintain a regular sleep schedule and create a relaxing "
            "routine before bedtime."
        ),
    },
    {
        "title": "Stay Physically Active",
        "description": (
            "Consider walking, stretching, dancing, or another movement "
            "activity you enjoy."
        ),
    },
    {
        "title": "Stay Connected",
        "description": (
            "Make time to connect with friends, family, or people you trust. "
            "Meaningful relationships can support well-being."
        ),
    },
    {
        "title": "Take Short Breaks",
        "description": (
            "During busy days, allow yourself short breaks to rest, breathe, "
            "and return to activities when you feel ready."
        ),
    },
    {
        "title": "Eat Regularly and Stay Hydrated",
        "description": (
            "When possible, maintain regular meals and drink enough water "
            "throughout the day."
        ),
    },
    {
        "title": "Make Time for What You Enjoy",
        "description": (
            "Reading, music, hobbies, or spending time outdoors can provide "
            "opportunities for enjoyment and relaxation."
        ),
    },
)


def custom_404(request, exception=None):
    return render(request, "core/404.html", status=404)


def custom_500(request):
    return render(request, "core/500.html", status=500)


def home(request):
    return render(request, "core/home.html")


def education(request):
    return render(request, "core/education.html")


def wellness_tips(request):
    tip = WELLNESS_TIPS[timezone.localdate().toordinal() % len(WELLNESS_TIPS)]
    return render(request, "core/wellness_tips.html", {"tip": tip})


def support_guide(request):
    return render(request, "core/support_guide.html")


def professional_directory(request):
    professionals = ProfessionalApplication.objects.filter(
        status=ProfessionalApplication.Status.APPROVED,
        consent_to_directory=True,
    ).select_related("applicant")

    query = request.GET.get("q", "").strip()
    title = request.GET.get("title", "").strip()
    organisation = request.GET.get("organisation", "").strip()

    if query:
        professionals = professionals.filter(
            Q(full_name__icontains=query)
            | Q(qualifications__icontains=query)
            | Q(biography__icontains=query)
        )
    if title:
        professionals = professionals.filter(professional_title__icontains=title)
    if organisation:
        professionals = professionals.filter(organisation__icontains=organisation)

    return render(request, "core/professional_directory.html", {
        "professionals": professionals,
        "query": query,
        "title": title,
        "organisation": organisation,
    })


@login_required
def self_awareness(request):
    form = SelfAwarenessForm(request.POST or None)
    result = None

    if request.method == "POST":
        if form.is_valid():
            answers = {
                field: str(form.cleaned_data[field])
                for field in ("mood", "energy", "stress", "connection")
            }
            score = sum(form.cleaned_data[field] for field in answers)

            if score <= 2:
                guidance = (
                    "Your responses suggest that things have felt relatively manageable "
                    "overall. Continue with routines that support your well-being."
                )
                heading = "A moment to notice what is working"
            elif score <= 5:
                guidance = (
                    "Your responses suggest a mixed pattern in the past seven days. "
                    "Consider rest, routine, trusted social support, or professional "
                    "guidance if concerns continue."
                )
                heading = "A mixed reflection"
            else:
                guidance = (
                    "Your responses suggest several areas may feel difficult. Consider "
                    "speaking with someone you trust or a qualified mental-health "
                    "professional. If you may be in immediate danger, seek urgent help."
                )
                heading = "Extra care may be helpful"

            ReflectionResponse.objects.create(
                user=request.user,
                answers=answers,
                score=score,
                guidance=guidance,
            )
            result = {"heading": heading, "guidance": guidance}
            messages.success(request, "Your reflection has been saved.")
        else:
            messages.error(request, "Please answer all four questions.")

    return render(request, "core/self_awareness.html", {
        "form": form,
        "result": result,
    })


def urgent_support(request):
    return render(request, "core/urgent_support.html")


def feedback(request):
    form = FeedbackForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.user = request.user if request.user.is_authenticated else None
        item.save()
        messages.success(request, "Thank you. Your feedback was submitted privately.")
        return redirect("feedback")
    return render(request, "core/feedback.html", {"form": form})


def _approved_application_for_user(user):
    application = ProfessionalApplication.objects.filter(
        applicant=user,
        status=ProfessionalApplication.Status.APPROVED,
    ).first()
    return application


@login_required
def appointment_request(request, application_id):
    professional = get_object_or_404(
        ProfessionalApplication.objects.select_related("applicant"),
        pk=application_id,
        status=ProfessionalApplication.Status.APPROVED,
        consent_to_directory=True,
    )
    form = AppointmentRequestForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        appointment = form.save(commit=False)
        appointment.requester = request.user
        appointment.professional = professional
        conflict = Appointment.objects.filter(
            professional=professional,
            requested_date=appointment.requested_date,
            requested_time=appointment.requested_time,
            status__in=[
                Appointment.Status.PENDING,
                Appointment.Status.ACCEPTED,
                Appointment.Status.RESCHEDULE_PROPOSED,
            ],
        ).exists()
        if conflict:
            form.add_error(
                "requested_time",
                "This professional already has an active request at that date and time.",
            )
        else:
            appointment.save()
            Notification.objects.create(
                user=professional.applicant,
                appointment=appointment,
                message=f"New appointment request from {request.user.username}.",
            )
            Notification.objects.create(
                user=request.user,
                appointment=appointment,
                message="Your appointment request was submitted and is pending review.",
            )
            messages.success(request, "Appointment request submitted.")
            return redirect("appointment_detail", appointment_id=appointment.pk)

    return render(request, "core/appointment_request.html", {
        "form": form,
        "professional": professional,
    })


@login_required
def appointment_detail(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related(
            "requester",
            "professional",
            "professional__applicant",
        ),
        pk=appointment_id,
    )
    professional_application = _approved_application_for_user(request.user)
    is_professional = (
        professional_application
        and appointment.professional_id == professional_application.pk
    )
    if request.user != appointment.requester and not is_professional:
        messages.error(request, "You are not authorized to view this appointment.")
        return redirect("dashboard")

    reschedule_form = RescheduleForm()
    if request.method == "POST":
        action = request.POST.get("action")

        if request.user == appointment.requester and action == "cancel":
            if appointment.status in (
                Appointment.Status.PENDING,
                Appointment.Status.ACCEPTED,
                Appointment.Status.RESCHEDULE_PROPOSED,
            ):
                appointment.status = Appointment.Status.CANCELLED
                appointment.save(update_fields=["status", "updated_at"])
                Notification.objects.create(
                    user=appointment.professional.applicant,
                    appointment=appointment,
                    message=f"{request.user.username} cancelled the appointment.",
                )
                messages.success(request, "Appointment cancelled.")
                return redirect("appointment_detail", appointment_id=appointment.pk)
            messages.error(
                request,
                "This appointment can no longer be cancelled.",
            )
        elif is_professional and action == "accept":
            if appointment.status != Appointment.Status.PENDING:
                messages.error(
                    request,
                    "Only pending appointments can be accepted.",
                )
            else:
                conflict = Appointment.objects.filter(
                    professional=appointment.professional,
                    requested_date=appointment.requested_date,
                    requested_time=appointment.requested_time,
                    status=Appointment.Status.ACCEPTED,
                ).exclude(pk=appointment.pk).exists()
                if conflict:
                    messages.error(request, "This time conflicts with another accepted appointment.")
                else:
                    appointment.status = Appointment.Status.ACCEPTED
                    appointment.save(update_fields=["status", "updated_at"])
                    Notification.objects.create(
                        user=appointment.requester,
                        appointment=appointment,
                        message="The professional accepted your appointment request.",
                    )
                    messages.success(request, "Appointment accepted.")
                    return redirect("appointment_detail", appointment_id=appointment.pk)
        elif is_professional and action == "reject":
            if appointment.status != Appointment.Status.PENDING:
                messages.error(
                    request,
                    "Only pending appointments can be rejected.",
                )
            else:
                appointment.status = Appointment.Status.REJECTED
                appointment.save(update_fields=["status", "updated_at"])
                Notification.objects.create(
                    user=appointment.requester,
                    appointment=appointment,
                    message="The professional declined your appointment request.",
                )
                messages.success(request, "Appointment rejected.")
                return redirect("appointment_detail", appointment_id=appointment.pk)
        elif is_professional and action == "reschedule":
            if appointment.status not in (
                Appointment.Status.PENDING,
                Appointment.Status.ACCEPTED,
            ):
                messages.error(
                    request,
                    "Only pending or accepted appointments can be rescheduled.",
                )
            else:
                reschedule_form = RescheduleForm(request.POST)
                if reschedule_form.is_valid():
                    appointment.status = Appointment.Status.RESCHEDULE_PROPOSED
                    appointment.proposed_date = reschedule_form.cleaned_data["proposed_date"]
                    appointment.proposed_time = reschedule_form.cleaned_data["proposed_time"]
                    appointment.save(update_fields=[
                        "status",
                        "proposed_date",
                        "proposed_time",
                        "updated_at",
                    ])
                    Notification.objects.create(
                        user=appointment.requester,
                        appointment=appointment,
                        message="The professional proposed a new appointment time.",
                    )
                    messages.success(request, "A new time was proposed.")
                    return redirect("appointment_detail", appointment_id=appointment.pk)
                messages.error(request, "Please provide a valid proposed date and time.")
        elif request.user == appointment.requester and action == "confirm_reschedule":
            if appointment.status == Appointment.Status.RESCHEDULE_PROPOSED:
                conflict = Appointment.objects.filter(
                    professional=appointment.professional,
                    requested_date=appointment.proposed_date,
                    requested_time=appointment.proposed_time,
                    status=Appointment.Status.ACCEPTED,
                ).exclude(pk=appointment.pk).exists()
                if conflict:
                    messages.error(request, "That proposed time is no longer available.")
                else:
                    appointment.requested_date = appointment.proposed_date
                    appointment.requested_time = appointment.proposed_time
                    appointment.status = Appointment.Status.ACCEPTED
                    appointment.save(update_fields=[
                        "requested_date",
                        "requested_time",
                        "status",
                        "updated_at",
                    ])
                    Notification.objects.create(
                        user=appointment.professional.applicant,
                        appointment=appointment,
                        message="The requester confirmed the proposed appointment time.",
                    )
                    messages.success(request, "Rescheduled appointment confirmed.")
                    return redirect("appointment_detail", appointment_id=appointment.pk)
            else:
                messages.error(
                    request,
                    "There is no proposed time to confirm.",
                )
        else:
            messages.error(
                request,
                "This action is not available for your role or appointment status.",
            )

    return render(request, "core/appointment_detail.html", {
        "appointment": appointment,
        "is_professional": is_professional,
        "reschedule_form": reschedule_form,
    })


@login_required
def appointment_list(request):
    professional_application = _approved_application_for_user(request.user)
    if professional_application:
        received = Appointment.objects.filter(
            professional=professional_application
        ).select_related("requester")
        requested = Appointment.objects.filter(requester=request.user)
    else:
        received = Appointment.objects.none()
        requested = Appointment.objects.filter(requester=request.user)
    unread_notifications = list(Notification.objects.filter(
        user=request.user,
        is_read=False,
    ))
    Notification.objects.filter(
        pk__in=[notification.pk for notification in unread_notifications],
    ).update(is_read=True)
    return render(request, "core/appointment_list.html", {
        "received": received,
        "requested": requested,
        "is_professional": professional_application is not None,
        "notifications": unread_notifications,
    })
