import logging
import os
import time

from django.http import HttpResponse

logger = logging.getLogger(__name__)

SLOW_THRESHOLD_MS = 500


class RequestTimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = int((time.monotonic() - start) * 1000)
        response["X-Response-Time-Ms"] = f"{duration_ms}ms"
        if duration_ms > SLOW_THRESHOLD_MS:
            logger.warning(
                "Slow request: %s %s -> %s in %sms",
                request.method,
                request.path,
                response.status_code,
                duration_ms,
            )
        return response


class MaintenanceMiddleware:
    ALLOWED_PATH_PREFIXES = (
        "/admin/",
        "/static/",
        "/media/",
        "/accounts/login/",
        "/accounts/logout/",
        "/webhooks/stripe/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not self._maintenance_on():
            return self.get_response(request)

        if self._request_is_allowed(request):
            return self.get_response(request)

        return self._maintenance_response()

    def _maintenance_on(self):
        value = (os.environ.get("MAINTENANCE_MODE") or "").strip().lower()
        return value in ("true", "1", "yes")

    def _request_is_allowed(self, request):
        for prefix in self.ALLOWED_PATH_PREFIXES:
            if request.path.startswith(prefix):
                return True
        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            return getattr(user, "is_staff", False) or getattr(
                user, "is_superuser", False
            )
        return False

    def _maintenance_response(self):
        response = HttpResponse(
            "<html><body>"
            "<h1>Site under maintenance</h1>"
            "<p>Please try again soon.</p>"
            "</body></html>",
            status=503,
            content_type="text/html",
        )
        response["Retry-After"] = "3600"
        return response