from django.utils.module_loading import import_string

from .conf import wallet_settings


def get_wallet_service():
    """
    Returns the configured WalletService class.
    Override via settings: dj_wallet['WALLET_SERVICE_CLASS']
    Example:
        WalletService = get_wallet_service()
        WalletService.deposit(wallet, amount)
    """
    return import_string(wallet_settings.WALLET_SERVICE_CLASS)


def get_transfer_service():
    """
    Returns the configured TransferService class.
    Override via settings: dj_wallet['TRANSFER_SERVICE_CLASS']
    """
    return import_string(wallet_settings.TRANSFER_SERVICE_CLASS)


def get_exchange_service():
    """
    Returns the configured ExchangeService class.
    Override via settings: dj_wallet['EXCHANGE_SERVICE_CLASS']
    """
    return import_string(wallet_settings.EXCHANGE_SERVICE_CLASS)


def get_purchase_service():
    """
    Returns the configured PurchaseService class.
    Override via settings: dj_wallet['PURCHASE_SERVICE_CLASS']
    """
    return import_string(wallet_settings.PURCHASE_SERVICE_CLASS)


def get_wallet_mixin():
    """
    Returns the configured WalletMixin class.
    Override via settings: dj_wallet['WALLET_MIXIN_CLASS']
    """
    return import_string(wallet_settings.WALLET_MIXIN_CLASS)
