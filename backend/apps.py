"""Django app configuration for the backend app."""

from django.apps import AppConfig


class BackendConfig(AppConfig):
    """AppConfig for backend."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "backend"
