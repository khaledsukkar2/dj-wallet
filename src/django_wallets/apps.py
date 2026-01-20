"""
Django app configuration for django_wallets.
"""

from django.apps import AppConfig


class DjangoWalletsConfig(AppConfig):
    """Configuration for the Django Wallets application."""

    name = "django_wallets"
    verbose_name = "Django Wallets"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """Import signals when the app is ready."""
        # Import signals to register them
        from . import signals  # noqa: F401
