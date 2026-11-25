from django.contrib import admin

from .models import Feedback, ReflectionResponse


@admin.register(ReflectionResponse)
class ReflectionResponseAdmin(admin.ModelAdmin):
    list_display = ("user", "score", "created_at")
    readonly_fields = ("user", "answers", "score", "guidance", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "guidance")


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("category", "user", "reviewed", "created_at")
    list_filter = ("category", "reviewed", "created_at")
    search_fields = ("user__username",)
    exclude = ("message",)
