
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .forms import RegistrationForm, ProfessionalApplicationForm
from .models import ProfessionalApplication


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")

    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {
        "form": form
    })


def user_login(request):
    next_url = request.POST.get("next", request.GET.get("next", ""))

    if request.method == "POST":
        form = AuthenticationForm(
            request,
            data=request.POST
        )

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect("dashboard")

    else:
        form = AuthenticationForm(request)

    return render(request, "accounts/login.html", {
        "form": form,
        "next": next_url,
    })


@require_POST
def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("login")


@login_required
def dashboard(request):
    from core.models import Appointment, Notification

    professional_application = ProfessionalApplication.objects.filter(
        applicant=request.user,
        status=ProfessionalApplication.Status.APPROVED,
    ).first()

    if professional_application:
        upcoming_appointments = Appointment.objects.filter(
            professional=professional_application,
            status__in=[
                Appointment.Status.PENDING,
                Appointment.Status.ACCEPTED,
                Appointment.Status.RESCHEDULE_PROPOSED,
            ],
        ).select_related("requester")[:5]
    else:
        upcoming_appointments = Appointment.objects.filter(
            requester=request.user,
            status__in=[
                Appointment.Status.PENDING,
                Appointment.Status.ACCEPTED,
                Appointment.Status.RESCHEDULE_PROPOSED,
            ],
        ).select_related("professional")[:5]

    notifications = Notification.objects.filter(
        user=request.user,
        is_read=False,
    )[:5]

    return render(request, "accounts/dashboard.html", {
        "professional_application": professional_application,
        "upcoming_appointments": upcoming_appointments,
        "notifications": notifications,
    })


@login_required
def professional_application(request):

    existing_application = ProfessionalApplication.objects.filter(
        applicant=request.user
    ).first()

    if existing_application:
        return render(request, "accounts/application_status.html", {
            "application": existing_application
        })

    if request.method == "POST":
        form = ProfessionalApplicationForm(request.POST)

        if form.is_valid():
            application = form.save(commit=False)
            application.applicant = request.user
            application.save()

            messages.success(
                request,
                "Your professional application has been submitted successfully."
            )

            return redirect("application_status")

    else:
        form = ProfessionalApplicationForm()

    return render(request, "accounts/professional_application.html", {
        "form": form
    })


@login_required
def application_status(request):

    application = ProfessionalApplication.objects.filter(
        applicant=request.user
    ).first()

    return render(request, "accounts/application_status.html", {
        "application": application
    })


@login_required
def account_settings(request):
    return render(request, "accounts/account_settings.html")


@login_required
@require_POST
def deactivate_account(request):
    request.user.is_active = False
    request.user.save(update_fields=["is_active"])
    logout(request)
    messages.success(
        request,
        "Your account was deactivated. Contact an administrator to restore access.",
    )
    return redirect("home")
