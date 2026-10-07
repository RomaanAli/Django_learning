"""Email transports for this project.

Why this file exists
--------------------
Free cloud plans block *outbound SMTP*:

* Render -- free instances block outbound SMTP ports 25/465/587.
* Railway -- Free, Trial and Hobby plans have SMTP disabled entirely; only
  Pro and above may open ports 25/465/587.

A plain SMTP backend can therefore never deliver from those hosts: the
connection just times out, producing the "SMTP error / not responding"
symptom even when the credentials are perfectly correct. HTTPS (port 443) is
always allowed, so Brevo's transactional email API is used as the primary
transport.

SMTP is NOT removed. ``FallbackEmailBackend`` keeps every transport in a list
and tries them in order, so the existing SMTP setup keeps working locally, on a
VPS and on paid Render instances:

    1. Brevo HTTPS API  -- works on every plan (needs BREVO_API_KEY)
    2. SMTP             -- used whenever the API is unavailable (EMAIL_HOST_*)
    3. Console          -- always last; prints the email into the log only

If a transport raises, the next one is tried. Only when *every* transport fails
does the error reach the caller, which is what lets
``accounts.views._send_otp_email`` roll the half-created account back and tell
the user to try again instead of failing silently.
"""

import os
from email.utils import parseaddr

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.utils.html import escape, strip_tags
from django.utils.module_loading import import_string

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

BREVO_SUCCESS_STATUSES = (200, 201, 202)


def describe_email_setup():
    """Return a one-line, secret-free summary of the active email setup.

    Printed into the deploy log at start-up (see ``CoreConfig.ready``) and by
    ``manage.py send_test_email``, so a misconfiguration shows up in the logs
    instead of only ever surfacing as "the OTP never arrived".
    """
    chain = getattr(settings, "EMAIL_BACKEND_CHAIN", [])
    brevo_key = "set" if getattr(settings, "BREVO_API_KEY", "") else "NOT SET"
    line = (
        f"[email] EMAIL_BACKEND={settings.EMAIL_BACKEND} chain={chain} "
        f"BREVO_API_KEY={brevo_key} "
        f"DEFAULT_FROM_EMAIL={settings.DEFAULT_FROM_EMAIL}"
    )
    pinned = (os.environ.get("EMAIL_BACKEND") or "").strip()
    if pinned:
        line += (
            " -- WARNING: EMAIL_BACKEND is set in the environment, which "
            f"pins {pinned} and DISABLES the fallback chain."
        )
    return line


class EmailDeliveryError(Exception):
    """Raised when a transport could not hand a message to the provider."""


class BrevoAPIBackend(BaseEmailBackend):
    """Send mail through Brevo's transactional email API over HTTPS.

    This is what makes email work on Render free instances, where outbound
    SMTP is blocked. It needs ``BREVO_API_KEY``
    and a sender address verified inside Brevo.
    """

    api_url = BREVO_API_URL

    def __init__(self, api_key=None, timeout=None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = (
            api_key or getattr(settings, "BREVO_API_KEY", "") or ""
        ).strip()
        self.timeout = timeout or getattr(settings, "EMAIL_TIMEOUT", 15)

    @staticmethod
    def _address(raw, name=None):
        """Turn ``'Name <a@b.com>'`` or ``'a@b.com'`` into Brevo's object.

        Note that ``parseaddr`` returns ``(realname, addr)`` -- the display
        name comes FIRST, the address second.
        """
        display_name, email = parseaddr(raw or "")
        address = {"email": (email or raw or "").strip()}
        label = name or display_name
        if label:
            address["name"] = label
        return address

    def _payload(self, message):
        """Build the JSON body Brevo expects for one ``EmailMessage``."""
        body = message.body or ""

        if getattr(message, "content_subtype", "plain") == "html":
            html_content = body
            text_content = strip_tags(body)
        else:
            html_content = None
            for content, mimetype in getattr(message, "alternatives", []):
                if mimetype == "text/html":
                    html_content = content
                    break
            text_content = body
        if html_content is None:
            html_content = f"<pre>{escape(text_content)}</pre>"

        payload = {
            "sender": self._address(
                message.from_email or settings.DEFAULT_FROM_EMAIL
            ),
            "to": [self._address(addr) for addr in message.to],
            "subject": message.subject,
            "textContent": text_content,
            "htmlContent": html_content,
        }
        if message.cc:
            payload["cc"] = [self._address(addr) for addr in message.cc]
        if message.bcc:
            payload["bcc"] = [self._address(addr) for addr in message.bcc]
        if message.reply_to:
            payload["replyTo"] = self._address(message.reply_to[0])
        return payload

    def _send_one(self, message):
        """POST one message to Brevo, raising ``EmailDeliveryError``."""
        payload = self._payload(message)
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers={
                    "api-key": self.api_key,
                    "accept": "application/json",
                    "content-type": "application/json",
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise EmailDeliveryError(
                f"Brevo API request failed: {exc}"
            ) from exc

        if response.status_code not in BREVO_SUCCESS_STATUSES:
            raise EmailDeliveryError(
                f"Brevo API returned HTTP {response.status_code}: "
                f"{(response.text or '')[:300]}"
            )
        return response

    def send_messages(self, email_messages):
        """Send every message; return how many Brevo accepted."""
        if not email_messages:
            return 0
        if not self.api_key:
            raise EmailDeliveryError(
                "BREVO_API_KEY is not set, so the Brevo API cannot send email."
            )

        sent = 0
        for message in email_messages:
            try:
                self._send_one(message)
            except EmailDeliveryError:
                if not self.fail_silently:
                    raise
                continue
            sent += 1
        return sent


class FallbackEmailBackend(BaseEmailBackend):
    """Try every backend in ``settings.EMAIL_BACKEND_CHAIN``, in order.

    This is what keeps the project resilient: Brevo's HTTPS API is tried
    first, and SMTP is only used when that fails -- so the SMTP settings that
    already exist stay valid and take over automatically wherever SMTP is
    actually reachable (local development, a VPS, paid Render instances).
    """

    def __init__(self, backend_paths=None, **kwargs):
        super().__init__(**kwargs)
        paths = backend_paths or getattr(settings, "EMAIL_BACKEND_CHAIN", [])
        self.backends = [
            import_string(path)(fail_silently=False) for path in paths
        ]

    @staticmethod
    def _name(backend):
        """Return the fully qualified class name of ``backend``."""
        return f"{type(backend).__module__}.{type(backend).__name__}"

    def send_messages(self, email_messages):
        """Return the first successful result, else raise the last error."""
        if not email_messages:
            return 0

        errors = []
        for backend in self.backends:
            name = self._name(backend)
            try:
                return backend.send_messages(email_messages)
            except Exception as exc:
                errors.append(f"{name}: {exc}")
                print(
                    f"[email] {name} failed ({exc}); trying the next "
                    "transport.",
                    flush=True,
                )

        if not self.fail_silently:
            raise EmailDeliveryError(
                "Every email transport failed: " + " | ".join(errors)
            )
        return 0
