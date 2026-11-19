"""Root URL configuration: Django admin under admin/, the backend app at the root."""

from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path

urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", admin.site.urls),
    path("", include("backend.urls")),
]
