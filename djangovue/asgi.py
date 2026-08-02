"""ASGI config for djangovue project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/

Author: Mike Borozdin (mikebz@)
"""

import os

from django.core.asgi import get_asgi_application
from django.core.handlers.asgi import ASGIHandler

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djangovue.settings")

application: ASGIHandler = get_asgi_application()
