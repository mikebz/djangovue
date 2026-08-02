"""Django app configuration for the backend app.

Author: Mike Borozdin (mikebz@)
"""

from django.apps import AppConfig


class BackendConfig(AppConfig):
    """AppConfig for backend.

    `default_auto_field` is not set here: Django 6.0 made `BigAutoField` the
    global default, so declaring it again would only restate the framework.
    """

    name: str = "backend"
