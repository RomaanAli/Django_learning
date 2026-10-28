
import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")



SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '').strip()
if not SECRET_KEY:
    # Fail closed: the old committed fallback key meant any deployment
    # without the env var shared one public secret. Render already sets
    # DJANGO_SECRET_KEY via generateValue; local runs must set it too.
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY is not set. Set it in .env (local) or in "
        "Render (service -> Environment, generateValue)."
    )

# Old expression was inverted: DJANGO_DEBUG='False' (the default) made
# DEBUG True. This flips prod DEBUG True -> False, which also stops
# Django serving media in prod (correct) and unmasks the W001 warning.
DEBUG = os.environ.get('DJANGO_DEBUG', 'False').strip().lower() in (
    'true', '1', 'yes',
)

ALLOWED_HOSTS = [
    'testserver',
    *[
        host.strip()
        for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,.onrender.com').split(',')
        if host.strip()
    ],
]

render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
if render_hostname and render_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_hostname)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Prod-gated HTTPS flags. Gated on actually running on Render (hostname
# present) as well as DEBUG off, so local runs and Django's test suite
# (which forces DEBUG=False) do not get SSL-redirect loops. HSTS preload
# is deliberately NOT set: it is irreversible and is a separate decision.
if not DEBUG and render_hostname:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

if render_hostname:
    render_origin = f"https://{render_hostname}"
    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'core',
    'courses',
    'accounts',
    'payments',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.RequestTimingMiddleware',
    'core.middleware.MaintenanceMiddleware',
]

ROOT_URLCONF = 'E_learning.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'E_learning.wsgi.application'



DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise ImproperlyConfigured(
        "DATABASE_URL is not set. This project requires PostgreSQL "
        "(SQLite is no longer supported).\n"
        "Locally, add to .env:\n"
        "  DATABASE_URL=postgresql://postgres:<password>"
        "@127.0.0.1:5432/elearning\n"
        "On Render, set DATABASE_URL from your Postgres instance "
        "(service -> Environment)."
    )
if not DATABASE_URL.startswith(("postgres://", "postgresql://")):
    raise ImproperlyConfigured(
        "DATABASE_URL must be a PostgreSQL URL starting with "
        f"postgresql:// (got scheme {DATABASE_URL.split(':', 1)[0]!r}). "
        "SQLite is no longer supported."
    )

DATABASES = {
    'default': dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
        conn_health_checks=True,
    ),
}



AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


CONSOLE_EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
SMTP_EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
BREVO_EMAIL_BACKEND = "core.mail_backends.BrevoAPIBackend"
CHAIN_EMAIL_BACKEND = "core.mail_backends.FallbackEmailBackend"

def _int_env(name, default):
    raw = (os.environ.get(name) or str(default)).strip()
    try:
        return int(raw)
    except ValueError:
        raise ImproperlyConfigured(
            f"{name} must be an integer, got {raw!r}."
        )


EMAIL_HOST = (os.environ.get("EMAIL_HOST") or "localhost").strip()
EMAIL_PORT = _int_env("EMAIL_PORT", 587)
EMAIL_HOST_USER = (os.environ.get("EMAIL_HOST_USER") or "").strip()
EMAIL_HOST_PASSWORD = (os.environ.get("EMAIL_HOST_PASSWORD") or "").strip()
EMAIL_USE_TLS = (
    (os.environ.get("EMAIL_USE_TLS") or "true").strip().lower() == "true"
)
EMAIL_TIMEOUT = _int_env("EMAIL_TIMEOUT", 15)
DEFAULT_FROM_EMAIL = (
    (os.environ.get("DEFAULT_FROM_EMAIL") or "").strip()
    or EMAIL_HOST_USER
    or "E-Learning <noreply@example.com>"
)

BREVO_API_KEY = (os.environ.get("BREVO_API_KEY") or "").strip()

_smtp_configured = bool(EMAIL_HOST_USER and EMAIL_HOST_PASSWORD)

EMAIL_BACKEND_CHAIN = []
if BREVO_API_KEY:
    EMAIL_BACKEND_CHAIN.append(BREVO_EMAIL_BACKEND)
if _smtp_configured:
    EMAIL_BACKEND_CHAIN.append(SMTP_EMAIL_BACKEND)
EMAIL_BACKEND_CHAIN.append(CONSOLE_EMAIL_BACKEND)

EMAIL_BACKEND = (os.environ.get("EMAIL_BACKEND") or "").strip()
if not EMAIL_BACKEND:
    EMAIL_BACKEND = (
        CHAIN_EMAIL_BACKEND
        if len(EMAIL_BACKEND_CHAIN) > 1
        else CONSOLE_EMAIL_BACKEND
    )

_delivery_required = (
    (os.environ.get("EMAIL_DELIVERY_REQUIRED") or "").strip().lower()
)
EMAIL_DELIVERY_REQUIRED = (
    _delivery_required == "true" if _delivery_required else not DEBUG
)



LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True



STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

STORAGES = {
    'default': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SITE_ID = 1
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

AUTH_USER_MODEL = 'accounts.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}


SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

LOGIN_REDIRECT_URL = "dashboard"
ACCOUNT_LOGOUT_REDIRECT_URL = "home"

ACCOUNT_LOGIN_METHODS = {"username", "email"}

SOCIALACCOUNT_LOGIN_ON_GET = True

SOCIALACCOUNT_ADAPTER = "accounts.adapters.SocialAccountAdapter"

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online", "prompt": "select_account"},
        "OAUTH_PKCE_ENABLED": True,
    }
}

_google_client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
_google_client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
if _google_client_id and _google_client_secret:
    SOCIALACCOUNT_PROVIDERS["google"]["APP"] = {
        "client_id": _google_client_id,
        "secret": _google_client_secret,
        "key": "",
    }


STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "").strip()
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
STRIPE_CURRENCY = os.environ.get("STRIPE_CURRENCY", "usd").strip().lower()

