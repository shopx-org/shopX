
# ShopX/settings.py
from pathlib import Path
import os
import environ

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ── Env ────────────────────────────────────────────────────────────────────────
# .env باید کنار manage.py باشد
env = environ.Env(
    DEBUG=(bool, True),
)
environ.Env.read_env(BASE_DIR / ".env")

# ── Core ───────────────────────────────────────────────────────────────────────
SECRET_KEY = env(
    "SECRET_KEY",
    default="django-insecure-change-me-in-.env",  # توصیه: در .env بگذار
)
DEBUG = env.bool("DEBUG", default=True)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])

# ── Apps ───────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'django.contrib.humanize',

    # local apps
    "home.apps.HomeConfig",
    "account.apps.AccountConfig",
    "OTP_app.apps.OtpAppConfig",
    "dashboards.apps.DashboardsConfig",
    "products.apps.ProductsConfig",
    
    # third-party
    "widget_tweaks",
    "mptt",
    "tree_queries",
    "colorfield",

]

# ── Middleware ─────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ShopX.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "ShopX.wsgi.application"

# ── Database (PostgreSQL @ 127.0.0.1:5433) ─────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="shopx"),
        "USER": env("POSTGRES_USER", default="shopx_user"),
        "PASSWORD": env("POSTGRES_PASSWORD", default=""),
        "HOST": env("POSTGRES_HOST", default="127.0.0.1"),
        "PORT": env.int("POSTGRES_PORT", default=5433),
        "CONN_MAX_AGE": 60,  # اتصال پایدار
        "OPTIONS": {
            "options": f"-c search_path={env('PG_SCHEMA', default='public')}"
        }
    }
}

# ── Auth/User ──────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "account.User"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
     "OPTIONS": {"user_attributes": ("phone", "first_name", "last_name", "email")}},
]

# ── i18n / tz ──────────────────────────────────────────────────────────────────
LANGUAGE_CODE = "fa"          # 'fa-ir' ممکنه variant رسمی نداشته باشه
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

# ── Cache (برای ریت‌لیمیت/OTP) ────────────────────────────────────────────────
ENABLE_RATE_LIMIT = False
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "shopx-rate-limit",
    }
}

# ── Static/Media ───────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
CKEDITOR_UPLOAD_PATH = "uploads/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── OTP / Ghasedak (از .env) ───────────────────────────────────────────────────
GHASEDAK_API_KEY = env("GHASEDAK_API_KEY", default="")
OTP_TEMPLATE_NAME = env("OTP_TEMPLATE_NAME", default="verifyphone")

# پنجره شمارش کل ارسال‌ها
OTP_WINDOW_SECONDS = 3600
OTP_MAX_ATTEMPTS_IN_WINDOW = 3

# dev/testing overrides
if DEBUG:
    OTP_TTL_SECONDS = 60
    OTP_RESEND_GAP_SEC = 1       # برای تست راحت
    OTP_MAX_RESENDS = 999
    OTP_BLOCK_DURATION = 2
    OTP_WINDOW_SECONDS = 3600
    OTP_MAX_ATTEMPTS_IN_WINDOW = 100000

# ── Security (برای دیپلوی واقعی فعال کن) ──────────────────────────────────────
