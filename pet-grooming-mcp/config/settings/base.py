"""Shared Django settings.

Layout follows django-boilerplate's convention (base / dev / prod split),
trimmed to what this project actually needs: a Postgres-backed session
store, Celery for follow-up jobs, and an admin surface. There is no
public HTTP API — the user-facing channel is the Discord bot.
"""
from pathlib import Path

from decouple import Csv, config


BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("DJANGO_SECRET_KEY", default="dev-insecure-key-change-me")
DEBUG = config("DJANGO_DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="*", cast=Csv())

DEFAULT_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "django_celery_beat",
    "django_celery_results",
]

CUSTOM_APPS = [
    "project.core",
    "project.grooming",
]

INSTALLED_APPS = DEFAULT_APPS + THIRD_PARTY_APPS + CUSTOM_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

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
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": config("DB_ENGINE", default="django.db.backends.sqlite3"),
        "NAME": config("DB_NAME", default=str(BASE_DIR / "db.sqlite3")),
        "USER": config("DB_USER", default=""),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST": config("DB_HOST", default=""),
        "PORT": config("DB_PORT", default=""),
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/django-static/"
STATIC_ROOT = BASE_DIR / "static"
MEDIA_URL = "/django-media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    # Celery already configures its own loggers; if we disable existing ones
    # its tracebacks get re-emitted character-by-character through our root
    # handler. Keep them and only add our project loggers on top.
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            # `%`-style formatter — robust against messages that contain
            # `{` characters (celery tracebacks, JSON payloads, etc.).
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "project": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "mcp_servers": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        # Celery has its own handlers; don't double-print by propagating.
        "celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

# ---- Celery ----------------------------------------------------------------
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = "django-db"
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

# ---- Grooming bot integrations --------------------------------------------
# Discord
DISCORD_TOKEN = config("DISCORD_TOKEN", default="")

# Google Sheets & Calendar
GOOGLE_SHEET_ID = config("GOOGLE_SHEET_ID", default="")
GOOGLE_SERVICE_ACCOUNT_FILE = config("GOOGLE_SERVICE_ACCOUNT_FILE", default="")
GOOGLE_CALENDAR_ID = config("GOOGLE_CALENDAR_ID", default="primary")
GOOGLE_CREDENTIALS_PATH = config("GOOGLE_CREDENTIALS_PATH", default="credentials.json")
GOOGLE_TOKEN_PATH = config("GOOGLE_TOKEN_PATH", default="token.pickle")

# LLM (OpenRouter)
OPENROUTER_API_KEY = config("OPENROUTER_API_KEY", default="")
OPENROUTER_MODEL = config("OPENROUTER_MODEL", default="anthropic/claude-3.5-sonnet")

# MCP server
MCP_SERVER_URL = config("MCP_SERVER_URL", default="http://localhost:8010/mcp")
MCP_HOST = config("MCP_HOST", default="0.0.0.0")
MCP_PORT = config("MCP_PORT", default=8010, cast=int)

# Followup defaults
FOLLOWUP_DELAY_HOURS = config("FOLLOWUP_DELAY_HOURS", default=24.0, cast=float)
