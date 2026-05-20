from django.http import JsonResponse
from django.shortcuts import render


def index(request):
    """
    serving up the main app page which loads the Vue.js from WebPack
    """
    context = {
        "data": "value",
    }
    return render(request, "index.html", context)


def healthz(_request):
    """Simple health endpoint for container readiness/liveness checks."""
    return JsonResponse({"status": "ok"})
