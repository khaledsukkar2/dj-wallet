"""
Django app configuration for dj_wallet.
"""

from django.apps import AppConfig


class DjangoWalletsConfig(AppConfig):
    """Configuration for the Django Wallets application."""

    name = "dj_wallet"
    verbose_name = "Django Wallets"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """Import signals when the app is ready."""
        # Import signals to register them
        from . import signals  # noqa: F401
