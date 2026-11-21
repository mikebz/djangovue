"""HTTP middleware for the backend application."""

from collections.abc import Callable

from django.http import HttpRequest, HttpResponseBase

from backend import views

HEALTHZ_PATH: str = "/healthz"


class HealthCheckMiddleware:
    """Serve `/healthz` probes before host validation and HTTPS redirect run.

    Container health checks (Docker `HEALTHCHECK`, Kubernetes kubelet, and
    load-balancer probes) request `/healthz` over plain HTTP and commonly send
    `localhost` or a container IP as `Host`. Placed first in `MIDDLEWARE`, this
    middleware handles `GET` and `HEAD` probes before `SecurityMiddleware` can
    redirect them to HTTPS and before `CommonMiddleware` rejects a `Host`
    outside `ALLOWED_HOSTS`.

    See https://adamj.eu/tech/2020/04/07/how-to-add-a-health-check-to-your-django-site/
    """

    def __init__(
        self,
        get_response: Callable[[HttpRequest], HttpResponseBase],
    ) -> None:
        """Store the next handler in the Django middleware chain.

        Args:
            get_response: The next middleware or view callable.

        """
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        """Short-circuit `GET` and `HEAD` probes for `/healthz`.

        Args:
            request: The incoming HTTP request.

        Returns:
            The health check response for `GET`/`HEAD` requests to `/healthz`,
            otherwise the response from the downstream middleware chain.

        """
        if request.path_info == HEALTHZ_PATH and request.method in ("GET", "HEAD"):
            return views.healthz(request)
        return self.get_response(request)
