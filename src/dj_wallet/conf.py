"""
Configuration settings for dj_wallet.

Settings can be overridden in your Django settings.py using the dj_wallet dictionary.
"""

from dataclasses import dataclass
from typing import Any

from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured


@dataclass
class WalletSettings:
    """Settings container for dj_wallet configuration."""

    # Number of decimal places for wallet balance calculations
    WALLET_MATH_SCALE: int = 8

    # Default currency code for new wallets
    WALLET_DEFAULT_CURRENCY: str = "USD"

    # Swappable service classes - use dotted path strings
    WALLET_SERVICE_CLASS: str = "dj_wallet.services.common.WalletService"
    TRANSFER_SERVICE_CLASS: str = "dj_wallet.services.transfer.TransferService"
    EXCHANGE_SERVICE_CLASS: str = "dj_wallet.services.exchange.ExchangeService"
    PURCHASE_SERVICE_CLASS: str = "dj_wallet.services.purchase.PurchaseService"

    # Transaction expiration settings
    PENDING_TRANSACTION_EXPIRY_HOURS: int = (
        24  # Hours before pending transactions can be expired
    )

    def __init__(self):
        """Initialize settings from Django settings if available."""
        user_settings = getattr(django_settings, "dj_wallet", {})

        for key, _ in self.__class__.__dataclass_fields__.items():
            # Map user setting keys (without WALLET_ prefix) to our attributes
            user_key = key.replace("WALLET_", "")
            if user_key in user_settings:
                setattr(self, key, user_settings[user_key])
            elif key in user_settings:
                setattr(self, key, user_settings[key])
            else:
                setattr(self, key, getattr(self.__class__, key))

        # Validate settings after initialization
        self._validate_settings()

    def _validate_settings(self):
        """
        Validate user-provided settings and raise ImproperlyConfigured for invalid values.
        """
        # Validate MATH_SCALE
        if not isinstance(self.WALLET_MATH_SCALE, int) or self.WALLET_MATH_SCALE < 0:
            raise ImproperlyConfigured(
                "dj_wallet['MATH_SCALE'] must be a non-negative integer. "
                f"Got: {self.WALLET_MATH_SCALE}"
            )

        if self.WALLET_MATH_SCALE > 30:
            raise ImproperlyConfigured(
                "dj_wallet['MATH_SCALE'] must be at most 30. "
                f"Got: {self.WALLET_MATH_SCALE}"
            )

        # Validate DEFAULT_CURRENCY
        if (
            not isinstance(self.WALLET_DEFAULT_CURRENCY, str)
            or len(self.WALLET_DEFAULT_CURRENCY) == 0
        ):
            raise ImproperlyConfigured(
                "dj_wallet['DEFAULT_CURRENCY'] must be a non-empty string. "
                f"Got: {self.WALLET_DEFAULT_CURRENCY}"
            )

        # Validate service class paths
        service_classes = [
            ("WALLET_SERVICE_CLASS", self.WALLET_SERVICE_CLASS),
            ("TRANSFER_SERVICE_CLASS", self.TRANSFER_SERVICE_CLASS),
            ("EXCHANGE_SERVICE_CLASS", self.EXCHANGE_SERVICE_CLASS),
            ("PURCHASE_SERVICE_CLASS", self.PURCHASE_SERVICE_CLASS),
        ]

        for name, value in service_classes:
            if not isinstance(value, str) or "." not in value:
                raise ImproperlyConfigured(
                    f"dj_wallet['{name}'] must be a valid dotted path string. "
                    f"Got: {value}"
                )

        # Validate PENDING_TRANSACTION_EXPIRY_HOURS
        if (
            not isinstance(self.PENDING_TRANSACTION_EXPIRY_HOURS, int)
            or self.PENDING_TRANSACTION_EXPIRY_HOURS < 1
        ):
            raise ImproperlyConfigured(
                "dj_wallet['PENDING_TRANSACTION_EXPIRY_HOURS'] must be a positive integer. "
                f"Got: {self.PENDING_TRANSACTION_EXPIRY_HOURS}"
            )

    def __getattr__(self, name: str) -> Any:
        """Fallback for attribute access."""
        raise AttributeError(f"'{type(self).__name__}' has no setting '{name}'")


# Singleton instance for import convenience
wallet_settings = WalletSettings()
