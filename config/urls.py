from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("core.urls")),
]

handler404 = "core.views.custom_404"
handler500 = "core.views.custom_500"
