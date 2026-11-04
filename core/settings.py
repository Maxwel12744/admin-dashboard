"""
Django settings for the core project (Django 5.2).

Everything that changes between your PC and the live server is read from
environment variables: your .env file locally, Vercel's Environment Variables online.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [v.strip() for v in os.getenv(name, default).split(",") if v.strip()]


# --- Core ---------------------------------------------------------------
DEBUG = env_bool("DEBUG", False)

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-insecure-key"
    else:
        raise RuntimeError("SECRET_KEY is not set. Add it to your .env file or Vercel settings.")

# Comma-separated, e.g. ALLOWED_HOSTS=yourproject.vercel.app
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
# Full origins with https://, e.g. CSRF_TRUSTED_ORIGINS=https://yourproject.vercel.app
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

# Secret used by the scheduled reminders URL (/cron/send-reminders/)
CRON_SECRET = os.getenv("CRON_SECRET", "")


# --- Apps ---------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serves static files online
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "dashboard.context_processors.notifications",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"


# --- Database (MySQL) ---------------------------------------------------
DB_OPTIONS = {"charset": "utf8mb4"}
# Many hosted MySQL services require SSL. Put their CA certificate file in your
# project (e.g. certs/ca.pem) and set DB_SSL_CA=certs/ca.pem
if os.getenv("DB_SSL_CA"):
    DB_OPTIONS["ssl"] = {"ca": str(BASE_DIR / os.getenv("DB_SSL_CA"))}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME", "dashboard_db"),
        "USER": os.getenv("DB_USER", "root"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": DB_OPTIONS,
    }
}


# --- Passwords ----------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --- Language and time --------------------------------------------------
LANGUAGE_CODE = "en-us"
# Reminder times are shown in this zone. Set TIME_ZONE in .env, e.g. Africa/Nairobi
TIME_ZONE = os.getenv("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True


# --- Static files -------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # `collectstatic` gathers files here

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}


# --- Uploaded pictures and media files ----------------------------------
# NOTE: Vercel has no permanent disk, so files uploaded here do not survive
# online. Local use is fine. For online use, switch to cloud storage.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"


# --- Login and sessions -------------------------------------------------
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

SESSION_EXPIRE_AT_BROWSER_CLOSE = True   # login ends when the browser closes
SESSION_COOKIE_AGE = 60 * 60 * 8         # or after 8 hours, whichever comes first


# --- Email --------------------------------------------------------------
# Locally emails print in the terminal. Online, set EMAIL_BACKEND in the
# environment to django.core.mail.backends.smtp.EmailBackend and fill in EMAIL_*.
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "My Dashboard <noreply@localhost>")
CRON_SECRET = os.getenv("CRON_SECRET", "")


# --- Security (only when DEBUG is off, i.e. online) ---------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Start at 0, then raise (e.g. 31536000) once HTTPS works everywhere.
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
    # Vercel sits behind a proxy that handles HTTPS: set BEHIND_PROXY=True there,
    # otherwise you get a redirect loop.
    if env_bool("BEHIND_PROXY", False):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")