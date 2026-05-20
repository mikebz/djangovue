"""HTTP views for backend application pages and health checks."""

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render


def index(request: HttpRequest) -> HttpResponse:
    """Render the index page that bootstraps the Vue frontend."""
    context: dict[str, str] = {
        "data": "value",
    }
    return render(request, "index.html", context)


def healthz(_request: HttpRequest) -> JsonResponse:
    """Simple health endpoint for container readiness/liveness checks."""
    return JsonResponse({"status": "ok"})
