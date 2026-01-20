"""
Configuration settings for django_wallets.

Settings can be overridden in your Django settings.py using the DJANGO_WALLETS dictionary.
"""

from dataclasses import dataclass
from typing import Any

from django.conf import settings as django_settings


@dataclass
class WalletSettings:
    """Settings container for django_wallets configuration."""

    # Number of decimal places for wallet balance calculations
    WALLET_MATH_SCALE: int = 8

    # Default currency code for new wallets
    WALLET_DEFAULT_CURRENCY: str = "USD"

    # Swappable service classes - use dotted path strings
    WALLET_SERVICE_CLASS: str = "django_wallets.services.common.WalletService"
    TRANSFER_SERVICE_CLASS: str = "django_wallets.services.transfer.TransferService"
    EXCHANGE_SERVICE_CLASS: str = "django_wallets.services.exchange.ExchangeService"
    PURCHASE_SERVICE_CLASS: str = "django_wallets.services.purchase.PurchaseService"


    def __init__(self):
        """Initialize settings from Django settings if available."""
        user_settings = getattr(django_settings, "DJANGO_WALLETS", {})

        for key, _ in self.__class__.__dataclass_fields__.items():
            # Map user setting keys (without WALLET_ prefix) to our attributes
            user_key = key.replace("WALLET_", "")
            if user_key in user_settings:
                setattr(self, key, user_settings[user_key])
            elif key in user_settings:
                setattr(self, key, user_settings[key])
            else:
                setattr(self, key, getattr(self.__class__, key))

    def __getattr__(self, name: str) -> Any:
        """Fallback for attribute access."""
        raise AttributeError(f"'{type(self).__name__}' has no setting '{name}'")


# Singleton instance for import convenience
wallet_settings = WalletSettings()
