"""
Django settings for running tests.
"""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = "test-secret-key-do-not-use-in-production"

DEBUG = True

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django_wallets",
    "tests.test_app",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        # "ENGINE": "django.db.backends.postgresql",
        # "NAME": "wallets",
        # "USER": "postgres",
        # "PASSWORD": "123",
        # "HOST": "localhost",
        # "PORT": "5432",
    }
}


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True
TIME_ZONE = "UTC"

AUTH_USER_MODEL = "test_app.User"

# Django Wallets settings
DJANGO_WALLETS = {
    "MATH_SCALE": 8,
    "DEFAULT_CURRENCY": "USD",
}
