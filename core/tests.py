"""Tests for the email transports and the deployment checks."""

from io import StringIO
from unittest import mock

import requests
from django.core.mail import EmailMessage
from django.core.mail.backends.base import BaseEmailBackend
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from core import checks
from core.mail_backends import (
    BrevoAPIBackend,
    EmailDeliveryError,
    FallbackEmailBackend,
    describe_email_setup,
)

BREVO_PATH = "core.mail_backends.BrevoAPIBackend"
SMTP_PATH = "django.core.mail.backends.smtp.EmailBackend"
CONSOLE_PATH = "django.core.mail.backends.console.EmailBackend"
CHAIN_PATH = "core.mail_backends.FallbackEmailBackend"

# Backends defined in this module, used to build small test chains.
FAILING_PATH = "core.tests.FailingBackend"
RECORDING_PATH = "core.tests.RecordingBackend"


class FailingBackend(BaseEmailBackend):
    """Always fails, like SMTP on a host that blocks outbound port 587."""

    def send_messages(self, email_messages):
        raise OSError("transport down")


class RecordingBackend(BaseEmailBackend):
    """Always succeeds and remembers how many messages it got."""

    sent = 0

    def send_messages(self, email_messages):
        RecordingBackend.sent += len(email_messages)
        return len(email_messages)


def _response(status=201, text=""):
    """Build a stand-in for ``requests.Response``."""
    response = mock.Mock()
    response.status_code = status
    response.text = text
    return response


def _message(**overrides):
    """Return a plain-text EmailMessage like the OTP one."""
    values = {
        "subject": "Verify Your E-Learning Account",
        "body": "Your OTP is 123456",
        "from_email": "E-Learning <noreply@example.com>",
        "to": ["student@example.com"],
    }
    values.update(overrides)
    return EmailMessage(**values)


@override_settings(
    BREVO_API_KEY="xkeysib-test",
    DEFAULT_FROM_EMAIL="E-Learning <noreply@example.com>",
    EMAIL_TIMEOUT=5,
)
class BrevoAPIBackendTests(SimpleTestCase):
    """The HTTPS transport that works on Render free plans."""

    @mock.patch("core.mail_backends.requests.post")
    def test_sends_through_the_https_api(self, post):
        post.return_value = _response()

        self.assertEqual(BrevoAPIBackend().send_messages([_message()]), 1)

        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://api.brevo.com/v3/smtp/email")
        self.assertEqual(kwargs["headers"]["api-key"], "xkeysib-test")
        self.assertEqual(kwargs["timeout"], 5)

        payload = kwargs["json"]
        self.assertEqual(
            payload["sender"],
            {"email": "noreply@example.com", "name": "E-Learning"},
        )
        self.assertEqual(payload["to"], [{"email": "student@example.com"}])
        self.assertEqual(payload["subject"], "Verify Your E-Learning Account")
        self.assertIn("123456", payload["textContent"])
        # A plain-text mail still gets an HTML part, so clients that block
        # plain text show something sensible.
        self.assertIn("123456", payload["htmlContent"])

    @mock.patch("core.mail_backends.requests.post")
    def test_html_mail_keeps_both_parts(self, post):
        post.return_value = _response()
        message = _message(body="<b>bold</b>")
        message.content_subtype = "html"

        BrevoAPIBackend().send_messages([message])

        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["htmlContent"], "<b>bold</b>")
        self.assertEqual(payload["textContent"], "bold")

    @mock.patch("core.mail_backends.requests.post")
    def test_cc_bcc_and_reply_to_are_forwarded(self, post):
        post.return_value = _response()
        message = _message(cc=["cc@example.com"], bcc=["bcc@example.com"])
        message.reply_to = ["reply@example.com"]

        BrevoAPIBackend().send_messages([message])

        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["cc"], [{"email": "cc@example.com"}])
        self.assertEqual(payload["bcc"], [{"email": "bcc@example.com"}])
        self.assertEqual(payload["replyTo"], {"email": "reply@example.com"})

    @mock.patch("core.mail_backends.requests.post")
    def test_http_error_is_reported(self, post):
        post.return_value = _response(400, '{"code":"invalid_parameter"}')

        with self.assertRaises(EmailDeliveryError) as ctx:
            BrevoAPIBackend().send_messages([_message()])

        self.assertIn("HTTP 400", str(ctx.exception))

    @mock.patch("core.mail_backends.requests.post")
    def test_network_error_is_reported(self, post):
        post.side_effect = requests.RequestException("connection reset")

        with self.assertRaises(EmailDeliveryError):
            BrevoAPIBackend().send_messages([_message()])

    @override_settings(BREVO_API_KEY="")
    def test_missing_api_key_is_reported(self):
        with self.assertRaises(EmailDeliveryError):
            BrevoAPIBackend().send_messages([_message()])

    @mock.patch("core.mail_backends.requests.post")
    def test_fail_silently_reports_zero(self, post):
        post.return_value = _response(500, "boom")

        self.assertEqual(
            BrevoAPIBackend(fail_silently=True).send_messages([_message()]), 0
        )

    @mock.patch("core.mail_backends.requests.post")
    def test_no_messages_means_no_request(self, post):
        self.assertEqual(BrevoAPIBackend().send_messages([]), 0)
        post.assert_not_called()


class FallbackEmailBackendTests(SimpleTestCase):
    """Brevo first, SMTP second, console last."""

    def setUp(self):
        RecordingBackend.sent = 0

    def test_smtp_is_used_when_brevo_fails(self):
        chain = FallbackEmailBackend(
            backend_paths=[FAILING_PATH, RECORDING_PATH]
        )

        self.assertEqual(chain.send_messages([_message()]), 1)
        self.assertEqual(RecordingBackend.sent, 1)

    def test_first_working_transport_wins(self):
        chain = FallbackEmailBackend(
            backend_paths=[RECORDING_PATH, FAILING_PATH]
        )

        self.assertEqual(chain.send_messages([_message()]), 1)
        self.assertEqual(RecordingBackend.sent, 1)

    def test_error_when_every_transport_fails(self):
        chain = FallbackEmailBackend(
            backend_paths=[FAILING_PATH, FAILING_PATH]
        )

        with self.assertRaises(EmailDeliveryError) as ctx:
            chain.send_messages([_message()])

        self.assertIn("Every email transport failed", str(ctx.exception))
        self.assertIn("FailingBackend", str(ctx.exception))

    def test_fail_silently_returns_zero(self):
        chain = FallbackEmailBackend(
            backend_paths=[FAILING_PATH], fail_silently=True
        )

        self.assertEqual(chain.send_messages([_message()]), 0)

    def test_empty_list_is_a_no_op(self):
        chain = FallbackEmailBackend(backend_paths=[FAILING_PATH])

        self.assertEqual(chain.send_messages([]), 0)

    @override_settings(
        EMAIL_BACKEND=CHAIN_PATH,
        EMAIL_BACKEND_CHAIN=[BREVO_PATH, SMTP_PATH, CONSOLE_PATH],
    )
    def test_chain_comes_from_the_setting(self):
        chain = FallbackEmailBackend()
        names = [type(backend).__name__ for backend in chain.backends]

        self.assertEqual(
            names, ["BrevoAPIBackend", "EmailBackend", "EmailBackend"]
        )


class EmailCheckTests(SimpleTestCase):
    """The deploy warnings must match what is really configured."""

    def _ids(self):
        return [issue.id for issue in checks.email_delivery_check(None)]

    @override_settings(
        EMAIL_BACKEND=CHAIN_PATH,
        EMAIL_BACKEND_CHAIN=[BREVO_PATH, SMTP_PATH, CONSOLE_PATH],
        BREVO_API_KEY="xkeysib-test",
        EMAIL_HOST_USER="user@example.com",
        EMAIL_HOST_PASSWORD="secret",
        EMAIL_DELIVERY_REQUIRED=True,
    )
    def test_brevo_first_chain_is_healthy(self):
        self.assertEqual(self._ids(), [])

    @override_settings(
        EMAIL_BACKEND=CHAIN_PATH,
        EMAIL_BACKEND_CHAIN=[CONSOLE_PATH],
        EMAIL_DELIVERY_REQUIRED=True,
    )
    def test_console_only_setup_is_flagged(self):
        self.assertIn("elearning.W001", self._ids())

    @override_settings(
        EMAIL_BACKEND=CHAIN_PATH,
        EMAIL_BACKEND_CHAIN=[BREVO_PATH, CONSOLE_PATH],
        BREVO_API_KEY="",
        EMAIL_DELIVERY_REQUIRED=True,
    )
    def test_brevo_without_api_key_is_flagged(self):
        self.assertIn("elearning.W003", self._ids())

    @override_settings(
        EMAIL_BACKEND=SMTP_PATH,
        EMAIL_HOST_USER="",
        EMAIL_HOST_PASSWORD="",
    )
    def test_smtp_without_credentials_is_flagged(self):
        self.assertIn("elearning.W002", self._ids())

    @override_settings(
        EMAIL_BACKEND=CHAIN_PATH,
        EMAIL_BACKEND_CHAIN=[SMTP_PATH, CONSOLE_PATH],
        BREVO_API_KEY="",
        EMAIL_DELIVERY_REQUIRED=True,
    )
    @mock.patch.dict("os.environ", {"RAILWAY_ENVIRONMENT": "production"})
    def test_smtp_only_on_railway_is_flagged(self):
        # This is the exact configuration that made OTP emails time out.
        self.assertIn("elearning.W004", self._ids())

    @override_settings(
        EMAIL_BACKEND=CHAIN_PATH,
        EMAIL_BACKEND_CHAIN=[BREVO_PATH, SMTP_PATH, CONSOLE_PATH],
        BREVO_API_KEY="xkeysib-test",
        EMAIL_DELIVERY_REQUIRED=True,
    )
    @mock.patch.dict("os.environ", {"RAILWAY_ENVIRONMENT": "production"})
    def test_brevo_present_makes_railway_happy(self):
        self.assertEqual(self._ids(), [])


class SendTestEmailCommandTests(SimpleTestCase):
    """The helper command used to prove delivery works."""

    @mock.patch("core.management.commands.send_test_email.send_mail")
    def test_reports_success(self, send_mail):
        send_mail.return_value = 1
        out = StringIO()

        call_command("send_test_email", "student@example.com", stdout=out)

        send_mail.assert_called_once()
        self.assertIn(
            "Test email sent to student@example.com", out.getvalue()
        )

    @mock.patch("core.management.commands.send_test_email.send_mail")
    def test_failure_is_a_command_error(self, send_mail):
        send_mail.side_effect = OSError("SMTP connection timed out")

        with self.assertRaises(CommandError) as ctx:
            call_command(
                "send_test_email", "student@example.com", stdout=StringIO()
            )

        self.assertIn("SMTP connection timed out", str(ctx.exception))

    @override_settings(BREVO_API_KEY="xkeysib-abcdefghijklmnopqrstuvwxyz")
    @mock.patch("core.management.commands.send_test_email.send_mail")
    def test_api_key_is_masked_not_leaked(self, send_mail):
        send_mail.return_value = 1
        out = StringIO()

        call_command("send_test_email", "student@example.com", stdout=out)

        printed = out.getvalue()
        self.assertIn("xkeysib-ab...", printed)
        self.assertNotIn("xkeysib-abcdefghijklmnopqrstuvwxyz", printed)


class DescribeEmailSetupTests(SimpleTestCase):
    """The start-up log line that makes a misconfiguration visible."""

    @override_settings(
        EMAIL_BACKEND=CHAIN_PATH,
        EMAIL_BACKEND_CHAIN=[BREVO_PATH, SMTP_PATH, CONSOLE_PATH],
        BREVO_API_KEY="xkeysib-test",
        DEFAULT_FROM_EMAIL="sender@example.com",
    )
    def test_reports_the_active_setup(self):
        line = describe_email_setup()

        self.assertIn(
            "EMAIL_BACKEND=core.mail_backends.FallbackEmailBackend", line
        )
        self.assertIn("BREVO_API_KEY=set", line)
        self.assertIn("sender@example.com", line)
        # It must never print the key itself.
        self.assertNotIn("xkeysib-test", line)

    @override_settings(BREVO_API_KEY="")
    def test_reports_a_missing_api_key(self):
        self.assertIn("BREVO_API_KEY=NOT SET", describe_email_setup())

    @mock.patch.dict(
        "os.environ",
        {"EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend"},
    )
    def test_warns_when_the_backend_is_pinned_by_the_environment(self):
        # The exact trap that made a cloud deploy keep using SMTP.
        line = describe_email_setup()

        self.assertIn("WARNING", line)
        self.assertIn("DISABLES the fallback chain", line)
