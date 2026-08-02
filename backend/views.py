# Author: Mike Borozdin (mikebz@)
"""HTTP views for backend application pages and health checks."""

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render


def index(request: HttpRequest) -> HttpResponse:
    """Render the index page that bootstraps the Vue frontend.

    Args:
        request: The incoming HTTP request.

    Returns:
        The HTTP response containing the rendered index page.

    """
    return render(request, "index.html")


def healthz(_request: HttpRequest) -> JsonResponse:
    """Provide a simple health endpoint for container readiness/liveness checks.

    Args:
        _request: The incoming HTTP request (unused).

    Returns:
        A JSON response indicating the service is healthy.

    """
    return JsonResponse({"status": "ok"})
