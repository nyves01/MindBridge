from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("education/", views.education, name="education"),
    path("wellness-tips/", views.wellness_tips, name="wellness_tips"),
    path("support-guide/", views.support_guide, name="support_guide"),
    path("professionals/", views.professional_directory, name="professional_directory"),
    path("self-awareness/", views.self_awareness, name="self_awareness"),
    path("urgent-support/", views.urgent_support, name="urgent_support"),
    path("feedback/", views.feedback, name="feedback"),
    path(
        "appointments/",
        views.appointment_list,
        name="appointment_list",
    ),
    path(
        "appointments/request/<int:application_id>/",
        views.appointment_request,
        name="appointment_request",
    ),
    path(
        "appointments/<int:appointment_id>/",
        views.appointment_detail,
        name="appointment_detail",
    ),
]
