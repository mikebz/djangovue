"""Security policy helpers for the settings module.

Builds the Content Security Policy and validates the HSTS preload settings.

Author: Mike Borozdin (mikebz@)
"""

from django.core.exceptions import ImproperlyConfigured
from django.utils.csp import CSP


def format_url_host(host: str) -> str:
    """Return a host that is safe to interpolate into a URL authority.

    A bare IPv6 literal has to be bracketed before a port can be appended, or
    the result is not a valid URL. django-vite builds its dev server URL by the
    same `host:port` concatenation, so bracketing once here keeps the asset URL
    and the CSP source that has to match it in agreement.

    Args:
        host: A hostname, IPv4 address, or IPv6 literal.

    Returns:
        The host, bracketed if it is an unbracketed IPv6 literal.

    Examples:
        >>> format_url_host("127.0.0.1")
        '127.0.0.1'
        >>> format_url_host("::1")
        '[::1]'
        >>> format_url_host("[::1]")
        '[::1]'

    """
    if ":" in host and not host.startswith("["):
        return f"[{host}]"
    return host


def build_csp_policy(
    *,
    dev_mode: bool,
    dev_server_host: str,
    dev_server_port: int,
) -> dict[str, list[str]]:
    """Return the Content-Security-Policy directives for the current run mode.

    The served page loads every asset from the same origin once the frontend is
    built, so the policy is `'self'` throughout. Running against the Vite dev
    server is the exception: modules are fetched from its origin, single-file
    component styles arrive as injected inline `<style>` elements, and hot
    module replacement opens a websocket back to it. Those three relaxations
    apply to dev mode only and never reach a built deployment.

    Args:
        dev_mode: Whether assets are served by the Vite dev server.
        dev_server_host: Host the Vite dev server listens on, already passed
            through `format_url_host`.
        dev_server_port: Port the Vite dev server listens on.

    Returns:
        A mapping of CSP directive name to its list of source expressions,
        shaped for the `SECURE_CSP` setting.

    Examples:
        >>> policy = build_csp_policy(
        ...     dev_mode=False, dev_server_host="127.0.0.1", dev_server_port=3000
        ... )
        >>> policy["script-src"] == [CSP.SELF, CSP.NONCE]
        True

    """
    # CSP.NONCE only becomes a real source when a template actually reads
    # {{ csp_nonce }}; unused, the middleware drops the placeholder. Listing it
    # is what lets a page add an inline script without loosening the policy.
    script_src: list[str] = [CSP.SELF, CSP.NONCE]
    style_src: list[str] = [CSP.SELF, CSP.NONCE]
    connect_src: list[str] = [CSP.SELF]

    if dev_mode:
        http_origin = f"http://{dev_server_host}:{dev_server_port}"
        websocket_origin = f"ws://{dev_server_host}:{dev_server_port}"
        script_src.append(http_origin)
        style_src += [http_origin, CSP.UNSAFE_INLINE]
        connect_src += [http_origin, websocket_origin]

    return {
        "default-src": [CSP.SELF],
        "script-src": script_src,
        "style-src": style_src,
        "connect-src": connect_src,
        # Vite inlines small assets as data: URIs during the production build.
        "img-src": [CSP.SELF, "data:"],
        "font-src": [CSP.SELF, "data:"],
        "base-uri": [CSP.SELF],
        "form-action": [CSP.SELF],
        "frame-ancestors": [CSP.NONE],
        "object-src": [CSP.NONE],
    }


# The browser preload list rejects any submission below a one-year max-age.
# https://hstspreload.org/#submission-requirements
HSTS_PRELOAD_MIN_SECONDS = 31_536_000


def validate_hsts_preload(
    *,
    preload: bool,
    include_subdomains: bool,
    max_age: int,
) -> None:
    """Check that an HSTS preload opt-in can actually be preloaded.

    The three HSTS settings are independent in Django, so a header advertising
    `preload` alongside a short max-age or without `includeSubDomains` is
    accepted silently and then rejected by the preload list. Failing at startup
    turns that into an error the operator can see.

    Args:
        preload: Whether the `preload` directive is requested.
        include_subdomains: Whether HSTS covers subdomains.
        max_age: The HSTS max-age in seconds.

    Returns:
        None.

    Raises:
        ImproperlyConfigured: If preload is requested without the two
            conditions the preload list requires.

    Examples:
        >>> validate_hsts_preload(
        ...     preload=True,
        ...     include_subdomains=True,
        ...     max_age=31536000,
        ... )

    """
    if not preload:
        return

    unmet: list[str] = []
    if not include_subdomains:
        unmet.append("SECURE_HSTS_INCLUDE_SUBDOMAINS must be enabled")
    if max_age < HSTS_PRELOAD_MIN_SECONDS:
        unmet.append(
            f"SECURE_HSTS_SECONDS must be at least {HSTS_PRELOAD_MIN_SECONDS}, "
            f"got {max_age}"
        )
    if unmet:
        raise ImproperlyConfigured(
            "SECURE_HSTS_PRELOAD is enabled but the browser preload list would "
            "reject this configuration: " + "; ".join(unmet) + "."
        )
